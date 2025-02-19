#!/usr/bin/env python
'''
# Script: evaluation_metrics.py
# Maintainer: Pepi Paraskevoulakou <e.paraskevoulakou@unipi.gr>
# Role: Lead Developer
# Copyright (c) 2023 Pepi Paraskevoulakou <e.paraskevoulakou@unipi.gr>
# Licensed under the MIT License.
# Source code development for the PhD thesis 

####################################################################
# Overview:

This scipt provides several metrics to measure the performance of
the trained forecasting models. Specifically uses:
1. MSE
2. RMSE
3.Coverage Probability
4. R2
'''

# Import necessary libraries
from time import time
from numpy.lib.shape_base import tile
import statsmodels.api as sm
import numpy as np
from sklearn.metrics import r2_score
import time
from sklearn.utils import resample


def calculate_mse(predictions, actuals):
    '''
     Mean Squared Error (MSE) is a commonly used metric for evaluating the performance of
     regression models. It measures the average of the squared differences between predicted
     values and actual values. A lower MSE indicates better model performance.

     Formula:
     MSE = Σ (y_actual - y_predicted)² / n

     Where:
     - Σ denotes the sum across all data points,
     - y_actual is the actual value,
     - y_predicted is the predicted value,
     - n is the number of data points.
    '''
    return np.mean(np.square(predictions - actuals))


# Root Mean Squared Error (RMSE)
def calculate_rmse(mse_value):
    '''
    ### Root Mean Squared Error (RMSE) is the square root of MSE. It provides a measure of the
    ### standard deviation of the errors between predicted and actual values. Like MSE, a lower
     RMSE indicates better model performance.

     Formula:
     RMSE = √MSE
    '''
    return np.sqrt(mse_value)


# R-squared (R2)
def calculate_r2_score(actuals, predicted):
    '''
    # Overview:
    # R-squared (R2) is a metric used to evaluate the goodness of fit of a regression model.
    # It measures the proportion of the variance in the dependent variable that is predictable
    # from the independent variables. R2 ranges from 0 to 1, where 0 indicates that the model
    # does not explain the variability in the data, and 1 indicates a perfect fit.

    # Formula:
    # R2 = 1 - (SSR / SST)
    ==================================
    # - R-squared ranges from 0 to 1.
    # - 0 indicates that the model does not explain any variability.
    # - 1 indicates that the model explains all the variability.
    '''
    r_squared = r2_score(actuals, predicted)
    return r_squared


def save_metrics(path_to_evaluation, target_resource,list_with_metrics, status):
    '''
     Function to save the results metrics
     mse
     rmse
     R2
    '''
    # Specify the file path
    file_path = f"metrics_{status}_{target_resource}.txt"

    try:
        # Open the file in write mode
        with open(path_to_evaluation+"/"+file_path, "w") as file:
            # Write each element to a new line
            for element in list_with_metrics:
                file.write(element + "\n")

    except Exception as e:

        print(e)


