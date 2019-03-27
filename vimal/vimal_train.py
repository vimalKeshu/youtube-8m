"""Binary for training Tensorflow models on the YouTube-8M dataset."""

import json
import os
import time

import eval_util
import export_model
import losses
import frame_level_models
import video_level_models
import readers
import tensorflow as tf
import tensorflow.contrib.slim as slim
from tensorflow.python.lib.io import file_io
from tensorflow import app
from tensorflow import flags
from tensorflow import gfile
from tensorflow import logging
from tensorflow.python.client import device_lib
import utils

FLAGS = flags.FLAGS

if __name__ == '__main__':
    # Dataset flags.
    flags.DEFINE_string("train_dir", "/tmp/yt8m_model/",
                        "The directory to save the model files in.")
    flags.DEFINE_string(
        "train_data_pattern", "",
        "File glob for the training dataset. If the files refer to Frame Level "
        "features (i.e. tensorflow.SequenceExample), then set --reader_type "
        "format. The (Sequence)Examples are expected to have 'rgb' byte array "
        "sequence feature as well as a 'labels' int64 context feature.")
    flags.DEFINE_string("feature_names", "mean_rgb", "Name of the feature "
                        "to use for training.")
    flags.DEFINE_string("feature_sizes", "1024", "Length of the feature vectors.")

    # Model flags
    flags.DEFINE_string("frame_features",False,
        "If set, then --train_data_pattern must be frame-level features."
        "Otherwise, --train_data_pattern must be aggrgated video-level"
        "features. The model must also be set approprietly (ie. read 3d vs 4d batches)")

    flags.DEFINE_string("model","LogisticModel",
        "Which architecture to use for the model. Models are defined "
        " in models.py")
    flags.DEFINE_string("start_new_model",False,
        "If set, this will not resume from a checkpointand will instead create a "
        " new model instance.")

    # Training flags
    flags.DEFINE_integer("num_gpu", 1,
                        "The maximum number of GPU devices to use for training. "
                        "Flag only applies if GPUs are installed")
    flags.DEFINE_integer("batch_size", 1024,
                       "How many examples to process per batch for training.")
    flags.DEFINE_string("label_loss", "CrossEntropyLoss",
                      "Which loss function to use for training the model.")
    flags.DEFINE_float(
      "regularization_penalty", 1.0,
      "How much weight to give to the regularization loss (the label loss has "
      "a weight of 1).")
    flags.DEFINE_float("base_learning_rate", 0.01,
                     "Which learning rate to start with.")
    flags.DEFINE_float("learning_rate_decay", 0.95,
                     "Learning rate decay factor to be applied every "
                     "learning_rate_decay_examples.")
    flags.DEFINE_float("learning_rate_decay_examples", 4000000,
                     "Multiply current learning rate by learning_rate_decay "
                     "every learning_rate_decay_examples.")
    flags.DEFINE_integer("num_epochs", 5,
                       "How many passes to make over the dataset before "
                       "halting training.")
    flags.DEFINE_integer("max_steps", None,
                       "The maximum number of iterations of the training loop.")
    flags.DEFINE_integer("export_model_steps", 1000,
                       "The period, in number of steps, with which the model "
                       "is exported for batch prediction.")
    
    # Other flags.
    flags.DEFINE_integer("num_readers", 8,
                       "How many threads to use for reading input files.")
    flags.DEFINE_string("optimizer", "AdamOptimizer",
                      "What optimizer class to use.")
    flags.DEFINE_float("clip_gradient_norm", 1.0, "Norm to clip gradients to.")
    flags.DEFINE_bool(
      "log_device_placement", False,
      "Whether to write the device on which every op will run into the "
      "logs on startup.")
    
    