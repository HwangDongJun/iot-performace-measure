import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
from tensorflow.keras import layers
import pickle
import efficientnet.tfkeras as efn


class action_recog(object):
    def __init__(self):
        self.weights = list()
        try:
            with open('Path to save the trained model weights file', 'rb') as fr:
                self.weights = pickle.load(fr)
        except (OSError, IOError) as e:
            print("not exist file!!")

        self.model_link = 'https://tfhub.dev/google/tf2-preview/mobilenet_v2/feature_vector/4'
        self.lr = 0.0001

    def set_model(self, vector_layer):
        model = tf.keras.Sequential([
            vector_layer,
            layers.Dense(5, activation='softmax')
        ])
        return model

    def build_model(self):
        feature_vector_url = self.model_link
        feature_vector_layer = hub.KerasLayer(feature_vector_url,
                                            input_shape=(224, 224, 3))
        
        feature_vector_layer.trainable = True

        made_model = self.set_model(feature_vector_layer)
        made_model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=self.lr),
            loss='categorical_crossentropy',
            metrics=['acc'])

        return made_model

    def train_model_evaluate(self):
        local_model = self.build_model()
        local_model.set_weights(self.weights)
        return local_model

    def get_model(self):
        return self.train_model_evaluate()