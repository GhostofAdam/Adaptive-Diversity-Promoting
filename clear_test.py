from __future__ import print_function
import keras
from keras.layers import AveragePooling2D, Input, Flatten
from keras.models import Model, load_model
from keras.datasets import cifar10, cifar100
import tensorflow as tf
import cleverhans.attacks as attacks
from cleverhans.utils_tf import model_eval
import os
from utils import *
from model import resnet_v1
from keras_wraper_ensemble import KerasModelWrapper


# Subtracting pixel mean improves accuracy
subtract_pixel_mean = True

# Computed depth from supplied model parameter n
n = 3
depth = n * 6 + 2
version = 1

# Model name, depth and version
model_type = 'ResNet%dv%d' % (depth, version)
print(model_type)

# Load the data.
if FLAGS.dataset == 'cifar10':
    (x_train, y_train), (x_test, y_test) = cifar10.load_data()
elif FLAGS.dataset == 'cifar100':
    (x_train, y_train), (x_test, y_test) = cifar100.load_data(label_mode='fine')

# Input image dimensions.
input_shape = x_train.shape[1:]

# Normalize data.
x_train = x_train.astype('float32') / 255
x_test = x_test.astype('float32') / 255

# If subtract pixel mean is enabled
clip_min = 0.0
clip_max = 1.0
if subtract_pixel_mean:
    x_train_mean = np.mean(x_train, axis=0)
    x_train -= x_train_mean
    x_test -= x_train_mean
    clip_min -= x_train_mean
    clip_max -= x_train_mean

# Convert class vectors to binary class matrices.
y_train = keras.utils.to_categorical(y_train, num_classes)
y_test = keras.utils.to_categorical(y_test, num_classes)


# Define input TF placeholder
x = tf.placeholder(tf.float32, shape=(None, 32, 32, 3))
y = tf.placeholder(tf.float32, shape=(None, num_classes))
sess = tf.Session()
keras.backend.set_session(sess)

# Prepare model pre-trained checkpoints directory.
save_dir = os.path.join(os.getcwd(), FLAGS.dataset+'_EE_LED_saved_models'+str(FLAGS.num_models)+'_lamda'+str(FLAGS.lamda)+'_logdetlamda'+str(FLAGS.log_det_lamda)+'_'+str(FLAGS.augmentation))
model_name = 'model.%s.h5' % str(FLAGS.epoch).zfill(3)
filepath = os.path.join(save_dir, model_name)
print('Restore model checkpoints from %s'% filepath)



#Creat model
model_input = Input(shape=input_shape)
model_dic = {}
model_out = []
feature_maps = []
for i in range(FLAGS.num_models):
    model_dic[str(i)] = resnet_v1(input=model_input, depth=depth, num_classes=num_classes, dataset=FLAGS.dataset)
    model_out.append(model_dic[str(i)][2])
    

model_output = keras.layers.concatenate(model_out)


model = Model(inputs=model_input, outputs=model_output)
model_ensemble = keras.layers.Average()(model_out)
model_ensemble = Model(input=model_input, output=model_ensemble)
models = []
for i in range(FLAGS.num_models):
    models.append(Model(inputs=model_input, outputs=model_out[i]))
eval_par = {'batch_size': 100}
model.load_weights(filepath)
for i in range(FLAGS.num_models):
    preds = models[i](x)
    acc = model_eval(sess, x, y, preds, x_test, y_test, args=eval_par)
    print('%dmodel_acc: %.3f '%(i,acc))
preds = model_ensemble(x)
acc = model_eval(sess, x, y, preds, x_test, y_test, args=eval_par)
print('ensemble_model_acc: %.3f '%(acc))


