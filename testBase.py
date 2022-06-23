import numpy as np
import tensorflow as tf
import random
from collections import deque
import os 
import datetime
from BaseLine import BaseLineModel
import tensorflow.keras.mixed_precision  as mixed_precision
# from testAgri import testNet
os.environ['CUDA_VISIBLE_DEVICES']='0'
# os.environ['TF_MIN_GPU_MULTIPROCESSOR_COUNT']= '2'

BATCH = 16 # 训练batch大小

    
def div_data():
    data = np.load('./data/data.npy',mmap_mode='r')
    labels = np.load('./data/label.npy',mmap_mode='r')
    data_div = deque()
    leng = labels.shape[0]
    for i in random.sample(range(leng),leng//4):
        data_div.append((np.array(data[i],dtype=np.float16),int(labels[i])))
    del data,labels
    return data_div

@tf.function
def trains(g_s,tru_s):
    with tf.GradientTape() as tape: #在这个空间里面计算梯度
        h_temp = classifier(g_s)
        # print(h_temp)
        ac_loss = tf.nn.sparse_softmax_cross_entropy_with_logits(tru_s,h_temp)
        ac_loss1 = tf.reduce_mean(ac_loss)
        ac_loss = optimizer_ac.get_scaled_loss(ac_loss1)

    gradients = tape.gradient(ac_loss, classifier.trainable_variables)
    gradients = optimizer_ac.get_unscaled_gradients(gradients)
    optimizer_ac.apply_gradients(zip(gradients, classifier.trainable_variables))
    return ac_loss1

def trainNet():
    # d_train = deque()  # Memory
    # tf.random.set_seed(42)
    eps=0
    
    # tensorboard
    train_log_dir='logs/base/'+datetime.datetime.now().strftime("%m%d-%H-%M")
    train_sum_writer = tf.summary.create_file_writer(train_log_dir)

    t= 100
    while eps < 40:
        data = div_data()

        # testAcc
        minibatch = random.sample(data, BATCH)
        g_s = tf.convert_to_tensor([d[0] for d in minibatch])
        tru_s = tf.convert_to_tensor([d[1] for d in minibatch])
        h_temp = classifier(g_s)
        acc = tru_s - tf.cast(tf.argmax(h_temp,-1),dtype=tf.int32)
        acc = 1 - np.count_nonzero(acc.numpy())/BATCH
        print(acc)
        with train_sum_writer.as_default():
            tf.summary.scalar('acc',acc,step=eps)

        # train
        for i in range(t):
            minibatch = random.sample(data, BATCH)
            g_s = tf.convert_to_tensor([d[0] for d in minibatch],dtype=tf.float16)
            tru_s = tf.convert_to_tensor([d[1] for d in minibatch])
            ac_loss = trains(g_s,tru_s)
            print("ac-loss = %f" % ac_loss,"t=",eps*t+i)
            if i % 5 == 4:
                with train_sum_writer.as_default():
                    tf.summary.scalar('CrossEn-loss',ac_loss,step=eps*t+i)

        classifier.save_wei()

        eps+=1

if __name__ == "__main__":
    # load_data()
    policy = mixed_precision.Policy('float32')
    mixed_precision.set_global_policy(policy)
    classifier = BaseLineModel()
    optimizer_ac = mixed_precision.LossScaleOptimizer(tf.keras.optimizers.Adam(learning_rate = 1e-4))
    trainNet()
    # testNet()