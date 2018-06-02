# -*- coding: utf-8 -*-
"""Facial.ipynb

Automatically generated by Colaboratory.

"""

!apt-get install -y -qq software-properties-common python-software-properties module-init-tools
!add-apt-repository -y ppa:alessandro-strada/ppa 2>&1 > /dev/null
!apt-get update -qq 2>&1 > /dev/null
!apt-get -y install -qq google-drive-ocamlfuse fuse
from google.colab import auth
auth.authenticate_user()
from oauth2client.client import GoogleCredentials
creds = GoogleCredentials.get_application_default()
import getpass
!google-drive-ocamlfuse -headless -id={creds.client_id} -secret={creds.client_secret} < /dev/null 2>&1 | grep URL
vcode = getpass.getpass()
!echo {vcode} | google-drive-ocamlfuse -headless -id={creds.client_id} -secret={creds.client_secret}

!mkdir -p drive
!google-drive-ocamlfuse drive

!pip install -q keras

import os

import numpy as np
from pandas.io.parsers import read_csv
from sklearn.utils import shuffle

train_ = 'drive/thesis/training.csv'
test_ = 'drive/thesis/test.csv'

def load(test=False, cols=None):
    fname = test_ if test else train_
    df = read_csv(os.path.expanduser(fname)) 
    
    df['Image'] = df['Image'].apply(lambda im: np.fromstring(im, sep=' '))

    if cols: 
        df = df[list(cols) + ['Image']]
  
    df = df.dropna()  

    X = np.vstack(df['Image'].values) / 255.
    X = X.astype(np.float32)

    if not test:  
        y = df[df.columns[:-1]].values
        y = (y - 48) / 48 
        X, y = shuffle(X, y, random_state=42)  
        y = y.astype(np.float32)
    else:
        y = None

    return X, y


X, y = load()

def load2d(test=False, cols=None):
  X, y = load(test, cols)
  X = X.reshape(-1, 96, 96, 1)
  return X, y

X, y = load2d()

from keras.layers import Convolution2D, MaxPooling2D, Flatten
from keras.layers import Dropout

from keras.models import Sequential
from keras.layers import Dense, Activation
from keras.optimizers import SGD


net1 = Sequential()

net1.add(Convolution2D(32, 3, 3, input_shape=(96, 96, 1)))
net1.add(Activation('relu'))
net1.add(MaxPooling2D(pool_size=(2, 2)))


net1.add(Convolution2D(64, 3, 3))
net1.add(Activation('relu'))
net1.add(MaxPooling2D(pool_size=(2, 2)))


net1.add(Convolution2D(128, 5, 5))
net1.add(Activation('relu'))
net1.add(MaxPooling2D(pool_size=(2, 2)))

net1.add(Flatten())
net1.add(Dense(300))
net1.add(Activation('relu'))
net1.add(Dense(300))
net1.add(Activation('relu'))
net1.add(Dense(30)) #15 coordinates, each one with (x,y).

sgd = SGD(lr=0.001, momentum=0.9, nesterov=True)
net1.compile(loss='mean_squared_error', optimizer=sgd)
hist1 = net1.fit(X, y, nb_epoch=1000, validation_split=0.2)

from matplotlib import pyplot
pyplot.plot(hist1.history['loss'], linewidth=2, label='train')
pyplot.plot(hist1.history['val_loss'], linewidth=2, label='valid')
pyplot.grid()
pyplot.legend()
pyplot.xlabel('epoch')
pyplot.ylabel('loss')
pyplot.ylim(1.5e-3, 1e-2)
pyplot.yscale('log')
pyplot.show()

#from keras.models import model_to
json_string = net1.to_json()
open('drive/thesis/net1_architecture.json', 'w').write(json_string)
net1.save_weights('drive/thesis/net1_weights.h5')

from keras.models import model_from_json
net1 = model_from_json(open('drive/thesis/net1_architecture.json').read())
net1.load_weights('drive/thesis/net1_weights.h5')

#Analyze facial key points
def plot_sample(x, y, axis):
    img = x.reshape(96, 96)
    axis.imshow(img, cmap='gray')
    axis.scatter(y[0::2] * 48 + 48, y[1::2] * 48 + 48, marker='x', s=10)
    
from matplotlib import pyplot

X_test, _ = load2d(test=True)
y_test = net1.predict(X_test)

fig = pyplot.figure(figsize=(6, 6))
fig.subplots_adjust(
    left=0, right=1, bottom=0, top=1, hspace=0.05, wspace=0.05)

for i in range(10,31):
    axis = fig.add_subplot(5, 5, i+1, xticks=[], yticks=[])
    plot_sample(X_test[i], y_test[i], axis)

pyplot.show()

#Flip the images.
from keras.preprocessing.image import ImageDataGenerator
class Flip_Image(ImageDataGenerator):
    flip_indices = [
        (0, 2), (1, 3),
        (4, 8), (5, 9), (6, 10), (7, 11),
        (12, 16), (13, 17), (14, 18), (15, 19),
        (22, 24), (23, 25),
        ]

    def next(self):
        X_batch, y_batch = super(FlippedImageDataGenerator, self).next()
        batch_size = X_batch.shape[0]
        indices = np.random.choice(batch_size, batch_size/2, replace=False)
        X_batch[indices] = X_batch[indices, :, :, ::-1]

        if y_batch is not None:
          
            y_batch[indices, ::2] = y_batch[indices, ::2] * -1

            # left_eye_center_x -> right_eye_center_x
            for a, b in self.flip_indices:
                y_batch[indices, a], y_batch[indices, b] = (
                    y_batch[indices, b], y_batch[indices, a]
                )

        return X_batch, y_batch

#CNN with data augmentation.
from keras.layers import Convolution2D, MaxPooling2D, Flatten
from keras.layers import Dropout

from keras.models import Sequential
from keras.layers import Dense, Activation
from keras.optimizers import SGD
from sklearn.cross_validation import train_test_split

X, y = load2d()
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

net2 = Sequential()

net2.add(Convolution2D(32, 3, 3, input_shape=(96, 96, 1)))
net2.add(Activation('relu'))
net2.add(MaxPooling2D(pool_size=(2, 2)))

net2.add(Convolution2D(64, 2, 2))
net2.add(Activation('relu'))
net2.add(MaxPooling2D(pool_size=(2, 2)))

net2.add(Convolution2D(128, 2, 2))
net2.add(Activation('relu'))
net2.add(MaxPooling2D(pool_size=(2, 2)))

net2.add(Flatten())
net2.add(Dense(300))
net2.add(Activation('relu'))
net2.add(Dense(300))
net2.add(Activation('relu'))
net2.add(Dense(30))

sgd = SGD(lr=0.01, momentum=0.9, nesterov=True)
net2.compile(loss='mean_squared_error', optimizer=sgd)
flipgen = Flip_Image()
hist3 = net2.fit_generator(flipgen.flow(X_train, y_train),
                             samples_per_epoch=X_train.shape[0],
                             nb_epoch=1000,
                             validation_data=(X_val, y_val))

json_string = net2.to_json()
open('drive/thesis/net2_architecture.json', 'w').write(json_string)
net2.save_weights('drive/thesis/net2_weights.h5')

#2nd model with Data augmentation VS 1st model.
from matplotlib import pyplot
pyplot.plot(hist3.history['loss'], linewidth=1, label='train2')
pyplot.plot(hist3.history['val_loss'], linewidth=1, label='valid2')
pyplot.grid()
pyplot.legend()


pyplot.plot(net1.history['loss'], linewidth=1, label='train1') #hist1
pyplot.plot(net1.history['val_loss'], linewidth=1, label='valid1')
pyplot.grid()
pyplot.legend()
pyplot.xlabel('epoch')
pyplot.ylabel('loss')
pyplot.ylim(2e-4, 5e-3)
pyplot.yscale('log')

pyplot.show()

#Change learning rate
from keras.callbacks import LearningRateScheduler

start_learning_rate = 0.05
end_learning_rate = 0.001
nb_epoch = 1000
learning_rates = np.linspace(start_learning_rate, end_learning_rate, nb_epoch)
change_learning_rate = LearningRateScheduler(lambda epoch: float(learning_rates[epoch]))

#CNN with learning rate change
from keras.layers import Convolution2D, MaxPooling2D, Flatten
from keras.layers import Dropout

from keras.models import Sequential
from keras.layers import Dense, Activation
from keras.optimizers import SGD
from sklearn.cross_validation import train_test_split

from keras import regularizers

X, y = load2d()
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

net3 = Sequential()

net3.add(Convolution2D(32, 3, 3, input_shape=(96, 96, 1)))
net3.add(Activation('relu'))
net3.add(MaxPooling2D(pool_size=(2, 2)))

net3.add(Convolution2D(64, 2, 2))
net3.add(Activation('relu'))
net3.add(MaxPooling2D(pool_size=(2, 2)))

net3.add(Convolution2D(128, 2, 2))
net3.add(Activation('relu'))
net3.add(MaxPooling2D(pool_size=(2, 2)))

net3.add(Flatten())
net3.add(Dense(300))
net3.add(Activation('relu'))
net3.add(Dense(300))
net3.add(Activation('relu'))
net3.add(Dense(30))

sgd = SGD(lr=0.01, momentum=0.9, nesterov=True)
net3.compile(loss='mean_squared_error', optimizer=sgd)
flipgen = Flip_Image()
hist4 = net3.fit_generator(flipgen.flow(X_train, y_train),
                             samples_per_epoch=X_train.shape[0],
                             nb_epoch=1000,
                             validation_data=(X_val, y_val),
                             callbacks = [change_learning_rate])

json_string = net3.to_json()
open('drive/thesis/net3_architecture.json', 'w').write(json_string)
net3.save_weights('drive/thesis/net3_weights.h5')

from matplotlib import pyplot

pyplot.plot(net1.history['loss'], linewidth=1, label='train1')
pyplot.plot(net1.history['val_loss'], linewidth=1, label='valid1')
pyplot.grid()
pyplot.legend()

pyplot.plot(hist3.history['loss'], linewidth=1, label='train2')
pyplot.plot(hist3.history['val_loss'], linewidth=1, label='valid2')
pyplot.grid()
pyplot.legend()

pyplot.plot(hist4.history['loss'], linewidth=1, label='train3')
pyplot.plot(hist4.history['val_loss'], linewidth=1, label='valid3')
pyplot.grid()
pyplot.legend()

pyplot.xlabel('epochs')
pyplot.ylabel('loss')
pyplot.ylim(2e-4, 1e-2)
pyplot.yscale('log')

pyplot.show()

#Model with early stopping and drop out layer
from keras.layers import Convolution2D, MaxPooling2D, Flatten
from keras.layers import Dropout

from keras.models import Sequential
from keras.layers import Dense, Activation
from keras.optimizers import SGD
from sklearn.cross_validation import train_test_split

from keras import regularizers
from keras.callbacks import EarlyStopping

X, y = load2d()
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

net4 = Sequential()

net4.add(Convolution2D(32, 3, 3, input_shape=(96, 96, 1)))
net4.add(Activation('relu'))
net4.add(MaxPooling2D(pool_size=(2, 2)))
net4.add(Dropout(0.1))

net4.add(Convolution2D(64, 2, 2))
net4.add(Activation('relu'))
net4.add(MaxPooling2D(pool_size=(2, 2)))
net4.add(Dropout(0.2))

net4.add(Convolution2D(128, 2, 2))
net4.add(Activation('relu'))
net4.add(MaxPooling2D(pool_size=(2, 2)))
net4.add(Dropout(0.3))

net4.add(Flatten())
net4.add(Dense(300))
net4.add(Activation('relu'))
net4.add(Dropout(0.5))
net4.add(Dense(300))
net4.add(Activation('relu'))
net4.add(Dense(30))

sgd = SGD(lr=0.01, momentum=0.9, nesterov=True)
net4.compile(loss='mean_squared_error', optimizer=sgd)
flipgen =Flip_Image()
early_stop = EarlyStopping(patience=50) #early stop patience = 50
hist5 = net4.fit_generator(flipgen.flow(X_train, y_train),
                             samples_per_epoch=X_train.shape[0],
                             nb_epoch=1000,
                             validation_data=(X_val, y_val),
                             callbacks = [change_learning_rate, early_stop])

json_string = net4.to_json()
open('drive/thesis/net4_architecture.json', 'w').write(json_string)
net4.save_weights('drive/thesis/net4_weights.h5')

from matplotlib import pyplot
pyplot.plot(hist4.history['loss'], linewidth=1, label='train3')
pyplot.plot(hist4.history['val_loss'], linewidth=1, label='valid3')
pyplot.grid()
pyplot.legend()

pyplot.plot(hist5.history['loss'], linewidth=1, label='train4')
pyplot.plot(hist5.history['val_loss'], linewidth=1, label='valid4')
pyplot.grid()
pyplot.legend()

pyplot.xlabel('epoch')
pyplot.ylabel('loss')
pyplot.ylim(2e-4, 1e-2)
pyplot.yscale('log')

pyplot.show()

#Analyze facial key points for net4

def plot_sample(x, y, axis):
    img = x.reshape(96, 96)
    axis.imshow(img, cmap='gray')
    axis.scatter(y[0::2] * 48 + 48, y[1::2] * 48 + 48, marker='x', s=10)

from matplotlib import pyplot

X_test, _ = load2d(test=True)
y_test = net4.predict(X_test)

fig = pyplot.figure(figsize=(6, 6))
fig.subplots_adjust(
    left=0, right=1, bottom=0, top=1, hspace=0.05, wspace=0.05)

for i in range(16):
    axis = fig.add_subplot(4, 4, i+1, xticks=[], yticks=[])
    plot_sample(X_test[i], y_test[i], axis)

pyplot.show()

