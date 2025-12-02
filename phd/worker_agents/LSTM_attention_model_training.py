#Import necessary libraries
from sklearn.model_selection import train_test_split
from keras import layers
import tensorflow as tf
import numpy as np
import pandas as pd
import time

class Attention(tf.keras.layers.Layer):
    def __init__(self, units, **kwargs):
        super(Attention, self).__init__(**kwargs)
        self.units = units
        self.W = tf.keras.layers.Dense(units)
        self.V = tf.keras.layers.Dense(1)

    def call(self, inputs):
        # Compute attention scores
        score = tf.nn.tanh(self.W(inputs))
        attention_weights = tf.nn.softmax(self.V(score), axis=1)

        # Apply attention weights to input
        context_vector = attention_weights * inputs
        context_vector = tf.reduce_sum(context_vector, axis=1)

        return context_vector
    
    def get_config(self):
        config = super(Attention, self).get_config()
        config.update({'units': self.units})
        return config


class DeepNeuralNetwork_Controller:
    def __init__(self, df:pd.DataFrame, features_cpu, features_memory):
        self.df = df
        self.updated_df = None
        self.training_features_cpu = features_cpu
        self.training_features_ram = features_memory
        self.all_features=[]
        self.T = None
        self.D = None

    
    def df_reformulation(self, target_metric:str):
        target_metric = target_metric.lower()
        if target_metric == "cpu" or target_metric == "cpu_usage" or target_metric=="cpu_consumption":
            updated_df = self.df[self.training_features_cpu]
            updated_df.loc[:, 'target_cpu'] = self.df['cpu']
        else:
            updated_df = self.df[self.training_features_ram]
            updated_df.loc[:, 'target_ram'] = self.df['mem']

        
        return updated_df
        

    def train_test_split_(self, updated_df, sequence_length):

        self.T =sequence_length
        self.D = len(list(updated_df.columns[:-1]))

        X_train, y_train = [], []
        for i in range(len(updated_df) - sequence_length + 1):
            sequence = updated_df.iloc[i:i + sequence_length]  # Extract a sequence based on length
            X_sequence = sequence.iloc[:, :-1].values  # Extract features for the sequence
            y_sequence = sequence.iloc[-1, -1]  # Extract the label for the sequence
            X_train.append(X_sequence)  # Append the feature sequence to X_train as a NumPy array
            y_train.append(y_sequence)  # Append the label to y_train


        X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.2)
        train_x, train_y= np.asarray(X_train), np.asarray(y_train)
        validation_x,validation_y  = np.asarray(X_val),np.asarray(y_val)

        return train_x, train_y, validation_x, validation_y

    
    def build_model(self):
        inputs = tf.keras.Input(shape=(self.T, self.D))
        x = tf.keras.layers.LSTM(64, return_sequences=True)(inputs)
        x = Attention(64)(x)
        x = tf.keras.layers.Dense(1)(x)
        model = tf.keras.Model(inputs=inputs, outputs=x)
        model.compile(optimizer="adam", loss="mse")

        print("\n[MODEL SUMMARY]")
        model.summary()

        print("\n[MODEL WEIGHTS]")
        for w in model.weights:
            print(w.name, w.shape)

        return model

    
# Register the custom layer
tf.keras.utils.register_keras_serializable('Attention', Attention)