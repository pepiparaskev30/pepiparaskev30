import pandas as pd
import tensorflow as tf 
from sklearn.model_selection import train_test_split
import numpy as np


class Transformer_Controller:
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
        
        # Transformer Encoder Block
        x = tf.keras.layers.MultiHeadAttention(num_heads=4, key_dim=64)(inputs, inputs)
        x = tf.keras.layers.LayerNormalization(epsilon=1e-6)(x)
        
        # Feedforward Network
        x_ffn = tf.keras.layers.Dense(128, activation='relu')(x)
        x_ffn = tf.keras.layers.Dense(64)(x_ffn)
        
        # Add & Normalize (Residual Connection)
        x = tf.keras.layers.Add()([x, x_ffn])
        x = tf.keras.layers.LayerNormalization(epsilon=1e-6)(x)

        # Global Pooling and Output Layer
        x = tf.keras.layers.GlobalAveragePooling1D()(x)
        outputs = tf.keras.layers.Dense(1)(x)

        model = tf.keras.Model(inputs=inputs, outputs=outputs)
        model.compile(optimizer="adam", loss="mse")
        
        return model
