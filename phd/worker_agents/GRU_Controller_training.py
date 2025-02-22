import numpy as np
import tensorflow as tf
import pandas as pd
from sklearn.model_selection import train_test_split


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

class GRU_Controller:
    def __init__(self, df: pd.DataFrame, features_cpu, features_memory):
        self.df = df
        self.updated_df = None
        self.training_features_cpu = features_cpu
        self.training_features_ram = features_memory
        self.all_features = []
        self.T = None
        self.D = None

    def df_reformulation(self, target_metric: str):
        target_metric = target_metric.lower()
        if target_metric in ["cpu", "cpu_usage", "cpu_consumption"]:
            updated_df = self.df[self.training_features_cpu]
            updated_df.loc[:, 'target_cpu'] = self.df['cpu']
        else:
            updated_df = self.df[self.training_features_ram]
            updated_df.loc[:, 'target_ram'] = self.df['mem']

        return updated_df

    def train_test_split_(self, updated_df, sequence_length):
        self.T = sequence_length
        self.D = len(list(updated_df.columns[:-1]))

        X_train, y_train = [], []
        for i in range(len(updated_df) - sequence_length + 1):
            sequence = updated_df.iloc[i:i + sequence_length]
            X_sequence = sequence.iloc[:, :-1].values
            y_sequence = sequence.iloc[-1, -1]
            X_train.append(X_sequence)
            y_train.append(y_sequence)

        X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.2)
        train_x, train_y = np.asarray(X_train), np.asarray(y_train)
        validation_x, validation_y = np.asarray(X_val), np.asarray(y_val)

        return train_x, train_y, validation_x, validation_y

    def build_model(self):
        inputs = tf.keras.Input(shape=(self.T, self.D))
        
        # GRU Layer
        x = tf.keras.layers.GRU(64, return_sequences=True)(inputs)
        
        # Attention Mechanism
        x_attention = Attention(64)(x)
        
        # Output Layer
        outputs = tf.keras.layers.Dense(1)(x_attention)

        model = tf.keras.Model(inputs=inputs, outputs=outputs)
        model.compile(optimizer="adam", loss="mse")
        
        return model
