#!/usr/bin/env python
'''
# Maintainer: Pepi Paraskevoulakou <e.paraskevoulakou@unipi.gr>
# Role: Lead Developer
Copyright (c) 2023 Pepi Paraskevoulakou <e.paraskevoulakou@unipi.gr>
Licensed under the MIT License.
Source code development for the PhD thesis 
Title/Name: elasticweightconsolidation.py 
'''

####################################################################
'''
This module and in general the entire code that resides here is for
handling the concept of incremmental learning. At this time, the 
elastic weight consolidation will be expolited to compare two nn models
and attach new knowledge incrementally in thenew model that will b used to
make the predictions.
'''

#import necessary libraries
import tensorflow as tf

# Elastic Weight Consolidation (EWC) functions
def get_params(model):
    return [tf.Variable(p.numpy()) for p in model.trainable_variables]

def update_params(model, prev_params):
    return [tf.Variable(p.numpy()) for p in model.trainable_variables]


def compute_fisher(model, dataloader, num_samples=100):
    fisher = [tf.zeros_like(p) for p in get_params(model)]
    for _ in range(num_samples):
        for data, target in dataloader:
            with tf.GradientTape() as tape:
                output = model(data)
                loss = tf.keras.losses.mean_squared_error(target, output)  # Use MSE loss
            grads = tape.gradient(loss, model.trainable_variables)
            params = get_params(model)
            for i in range(len(fisher)):
                fisher[i] += tf.square(grads[i])

    fisher = [f / (num_samples * len(dataloader)) for f in fisher]
    return fisher

def ewc_penalty(params, prev_params, fisher, fisher_multiplier):
    penalty = 0
    for i in range(len(params)):
        penalty += (fisher_multiplier * fisher[i] * tf.square(params[i] - prev_params[i])).numpy().sum()
    return penalty