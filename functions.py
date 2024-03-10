import sys, os, datetime, pickle, time
import string, pdb, tqdm
import random, cv2, keras, os.path
import pandas as pd
import numpy as np

import plotly.graph_objects as go

from evidently.dashboard import Dashboard
from evidently.dashboard.tabs import ProbClassificationPerformanceTab

from sklearn.metrics import classification_report, confusion_matrix
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score

import keras
import tensorflow as tf
from tensorflow.keras import models
from tensorflow.keras import layers
from tensorflow.keras import optimizers
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping


def simulations(num_simulations, model, train_f, train_l, valid_f, valid_l, ass_f, ass_l):

    learning_rate   = 2e-4
    BATCH_SIZE      = 50
    STEPS_PER_EPOCH = train_l.size / BATCH_SIZE
    SAVE_PERIOD     = 1
    epochs = 100

    #
    loss = tf.keras.losses.categorical_crossentropy
    # loss = tf.keras.losses.binary_crossentropy

    optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)

    classes = ['OK', 'NOK']
    
    precision_scores = []
    recall_scores = []
    f1_scores = []
    accuracy_scores = []
    confusion_matrices = []

    save_path = os.path.join(os.getcwd(), 'ZN_1D_imgs/')
    modelPath = os.path.join(os.getcwd(), 'ZN_1D_imgs/bestModel.h5')

    # Perform 10 simulations of network training
    for _ in range(num_simulations):
        # Create the model
        model = model

        # Compile the model
        model.compile(loss=loss, optimizer=optimizer, metrics=['accuracy'])

        # Configure checkpoints
        checkpoint = keras.callbacks.ModelCheckpoint(
            modelPath,
            monitor='val_loss',
            verbose=1,
            save_best_only=True,
            save_weights_only=False,
            mode='auto',
            save_freq=int(SAVE_PERIOD * STEPS_PER_EPOCH)
        )

        earlystopping = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            min_delta=0.0001,
            patience=25,
            restore_best_weights=True
        )

        callbacksList = [checkpoint, earlystopping]

        # Train the model
        hist = model.fit(train_f, train_l, epochs=epochs, batch_size=BATCH_SIZE,
                        validation_data=(valid_f, valid_l), callbacks=callbacksList) 

        # Save training history
        with open(os.path.join(save_path, f"hist_{_}.pkl"), "wb") as file:
            pickle.dump(hist.history, file)

        # Get predictions on the independent set
        yPredClass = np.argmax(model.predict(ass_f), axis=-1)
        yTestClass = np.argmax(ass_l, axis=1)

        # Calculate metrics per class
        precision = precision_score(yTestClass, yPredClass, average=None)
        recall = recall_score(yTestClass, yPredClass, average=None)
        f1 = f1_score(yTestClass, yPredClass, average=None)
        accuracy = accuracy_score(yTestClass, yPredClass)
        confusion_matrix_sim = confusion_matrix(yTestClass, yPredClass)

        # Store metrics for this simulation
        precision_scores.append(precision)
        recall_scores.append(recall)
        f1_scores.append(f1)
        accuracy_scores.append(accuracy)
        confusion_matrices.append(confusion_matrix_sim)

    # Convert lists to arrays to facilitate calculation of mean and standard deviation
    precision_scores = np.array(precision_scores)
    recall_scores = np.array(recall_scores)
    f1_scores = np.array(f1_scores)
    accuracy_scores = np.array(accuracy_scores)
    confusion_matrices = np.array(confusion_matrices)

    # Calculate mean and standard deviation of metrics per class
    mean_precision = np.mean(precision_scores, axis=0)
    mean_recall = np.mean(recall_scores, axis=0)
    mean_f1 = np.mean(f1_scores, axis=0)
    mean_accuracy = np.mean(accuracy_scores)
    mean_confusion_matrix = np.mean(confusion_matrices, axis=0)

    std_dev_precision = np.std(precision_scores, axis=0)
    std_dev_recall = np.std(recall_scores, axis=0)
    std_dev_f1 = np.std(f1_scores, axis=0)
    std_dev_accuracy = np.std(accuracy_scores)
    std_dev_confusion_matrix = np.std(confusion_matrices, axis=0)

    # Print results
    print("\nMean Precision:", mean_precision)
    print("Mean Recall:", mean_recall)
    print("Mean F1-score:", mean_f1)
    print("Mean Accuracy:", mean_accuracy)
    print("Mean Conf. Matrix", mean_confusion_matrix)

    print("\nStandard Deviation of Precision:", std_dev_precision)
    print("Standard Deviation of Recall:", std_dev_recall)
    print("Standard Deviation of F1-score:", std_dev_f1)
    print("Standard Deviation of Accuracy:", std_dev_accuracy)
    print("Standart Conf. Matrix", std_dev_confusion_matrix)

    # Obtain a plot to visualize results
    metrics_plot = plot_metrics(mean_precision, std_dev_precision, mean_recall, std_dev_recall, mean_f1, std_dev_f1, classes)

    conf_plot = plot_confusion_matrix(mean_confusion_matrix, std_dev_confusion_matrix, classes)

    return metrics_plot, conf_plot, mean_precision, std_dev_precision, mean_recall, std_dev_recall, mean_f1, std_dev_f1, mean_accuracy, std_dev_accuracy


def plot_metrics(mean_precision, std_dev_precision, mean_recall, std_dev_recall, mean_f1, std_dev_f1, classes):
    metrics = {
        'Precision': {
            'mean': mean_precision,
            'stddev': std_dev_precision,
            'color': 'rgb(153, 43, 132)'},
        'Recall': {
            'mean': mean_recall,
            'stddev': std_dev_recall,
            'color': 'rgb(255, 153, 51)'},
        'F1-Score': {
            'mean': mean_f1,
            'stddev': std_dev_f1,
            'color': 'rgb(51, 153, 255)'}}

    # Create the figure
    fig = go.Figure()

    # Add bars for each metric
    for metric_name, metric_data in metrics.items():
        fig.add_trace(go.Bar(
            x=classes,
            y=metric_data['mean'],
            error_y=dict(type='data', array=metric_data['stddev'], visible=True),
            name=metric_name,
            marker_color=metric_data['color']))

    # Update the layout of the plot
    fig.update_layout(
        title='Metrics per class',
        xaxis=dict(title='Classes'),
        yaxis=dict(title='Value'),
        yaxis_tickformat=".2%",
        barmode='group',
        bargap=0.15)

    return fig


def plot_confusion_matrix(mean_confusion_matrix, std_dev_confusion_matrix, classes):
    fig = go.Figure(data=go.Heatmap(z=mean_confusion_matrix,
                                     zmin=mean_confusion_matrix.min(),
                                     zmax=mean_confusion_matrix.max(),
                                     hoverongaps=False,
                                     colorscale='Blues',
                                     colorbar=dict(title='Count')))

    annotations = []

    for i in range(mean_confusion_matrix.shape[0]):
        for j in range(mean_confusion_matrix.shape[1]):
            annotation = {
                'x': j,
                'y': i,
                'text': f"{mean_confusion_matrix[i, j]:.2f} ± {std_dev_confusion_matrix[i, j]:.2f}",
                'showarrow': False,
                'font': {'color': 'black'}
            }
            annotations.append(annotation)

    fig.update_layout(title='Confusion Matrix (Mean +/- Standard Deviation)',
                      xaxis=dict(tickvals=list(range(len(classes))), ticktext=classes),
                      yaxis=dict(tickvals=list(range(len(classes))), ticktext=classes),
                      annotations=annotations)
    return fig
