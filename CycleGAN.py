# -*- coding: utf-8 -*-
"""CycleGAN

Automatically generated by Colaboratory.
Original file is located at
    https://colab.research.google.com/drive/1L25yWyDVlS_Cn12VTeu7xmd0QD9V9kYt
"""

# Import relevant libraries and fix the random seeds of both tensorflow and numpy!
import tensorflow as tf; tf.set_random_seed(0); import numpy as np; np.random.seed(0);
import matplotlib.pyplot as plt; import pylab; import os; from os import listdir; 
import warnings; warnings.filterwarnings("ignore"); import random;

# Some Global Variables
batch_sz = 1; img_height = 256; img_width = 256; img_channels = 3; pool_size = 50;
mon_rel_dir = "./Dataset/Monet/"; cez_rel_dir = "./Dataset/Cezzane/";

# File names of the corresponding dataset (Monet painitings and Cezzane paintings)
mon_file_name = [mon_rel_dir + s for s in os.listdir(mon_rel_dir)]; 
cez_file_name = [cez_rel_dir + s for s in os.listdir(cez_rel_dir)];

# Create a global array to store the images generated by the Generator while training
fake_a_arr = fake_b_arr = np.zeros((pool_size, batch_sz, img_height, img_width, img_channels));


def summary(var, name):
    
    """
    Arguments:
    var:  Variable whose summary will get plotted on tensorboard
    name: Variable's name that will be assigned to it
    
    """  
    
    with tf.variable_scope(name):
#       Mean and Standard Deviation of the variable 
        mu = tf.reduce_mean(var); sigma = tf.sqrt(tf.reduce_mean(tf.square(var - mu)));
#       Histogram plot of the variable
        tf.summary.histogram('Histogram', var); tf.summary.scalar("Mean", mu); tf.summary.scalar("Std_dev", sigma);


def get_tensor_slices(tensor): 
    
    """
    Arguments:
    Tensor:  Simple or Nested structures of tensors 
    
    Returns:
    Dataset: Dataset format of the above tensor 
    """
	return tf.data.Dataset.from_tensor_slices(tensor)


# Get the iterators corresponding to both the dataset
def get_iterators(sess):
    
    #  Shuffle and repeat the datset, Apply the mapping transformation, Batch and prefetch (one or n) of them

    """
    Arguments:
    sess:           Session of tensorflow
    
    Returns:
    handle:         A scalar tf.Tensor of type tf.string that evaluates to a handle 
    next_element:   A nested structure of tf.Tensors representing the next element
    train_iterator: Iterator corresponding to the training dataset
    train_handle:   String-valued tf.Tensor that represents the train iterator
    """

    mon_dataset = get_tensor_slices(tf.constant(mon_file_name)); cez_dataset = get_tensor_slices(tf.constant(cez_file_name));

    mon_dataset = mon_dataset.shuffle(500).repeat(); 
    mon_dataset = mon_dataset.map(lambda x: tf.subtract(tf.div(tf.image.resize_images(tf.image.decode_jpeg(tf.read_file(x)), \
										      [img_height, img_width]), 127.5), 1))

    cez_dataset = cez_dataset.shuffle(500).repeat();
    cez_dataset = cez_dataset.map(lambda x: tf.subtract(tf.div(tf.image.resize_images(tf.image.decode_jpeg(tf.read_file(x)), \
										      [img_height, img_width]), 127.5), 1))

    mon_dataset = (mon_dataset.batch(batch_sz)).prefetch(1); cez_dataset = (cez_dataset.batch(batch_sz)).prefetch(1);
    
    handle = tf.placeholder(tf.string, shape = []);
    iterator = tf.data.Iterator.from_string_handle(handle, output_types = mon_dataset.output_types, 
						   output_shapes = mon_dataset.output_shapes)
    next_element = iterator.get_next();
    
    mon_iterator = mon_dataset.make_initializable_iterator(); mon_handle = sess.run(mon_iterator.string_handle());
    cez_iterator = cez_dataset.make_initializable_iterator(); cez_handle = sess.run(cez_iterator.string_handle());
    
    return handle, next_element, mon_iterator, mon_handle, cez_iterator, cez_handle;


def conv_2d(inp_ten, kernel_sz = 4, strides = 1, out_channels = 64, is_conv = True, is_act = True, activation = "relu", 
            leak_param = 1/5.5, is_norm = True, normalization = "instance", use_bias = False, padding = "SAME"):

    """
    Arguments:
    inp_ten:       Input Tensor
    kernel_sz:     Integer or tuple/list of 2 integers, specifying the height and width of the 2D convolution window
    strides:       Integer or tuple/list of 2 integers, specifying the strides of the convolution along the height and width
    out_channels:  Integer, the dimensionality of the output space
    is_conv:       Boolean, whether to perform convolution or not
    is_norm:       Boolean, whether to normalize the data or not
    normalization: Type of normalization, supports batch and instance normalization
    is_act:        Boolean, whether to apply non-linear activation functions or not
    activation:    Type of activation function, supports Leaky_ReLU, ReLU and Elu
    leak_param:    Integer, Leakiness to use in case of Leaky ReLU
    padding:       "Valid" (Reflection padding) or "SAME"(Constant padding filled with 0s)
    use_bias:      Boolean, whether to use bias or not!
    
    Returns:
    x:             Output Tensor
    """

	if padding == "VALID":
		inp_ten = tf.pad(inp_ten, [[0,0],[kernel_sz//2, kernel_sz//2],[kernel_sz//2, kernel_sz//2],[0,0]], 'REFLECT'); 
    
	if is_conv:
		x = tf.layers.conv2d(inputs = inp_ten, filters = out_channels, kernel_size = kernel_sz, strides = strides, padding = padding,
		    use_bias = use_bias, kernel_initializer = tf.random_normal_initializer(mean = 0, stddev = 0.02, dtype = tf.float32));
    
	if is_norm:
		if normalization == "batch": x = tf.layers.batch_normalization(x, momentum = 0.9, epsilon = 1e-5, training = train_mode);
		elif normalization == "instance": x = tf.contrib.layers.instance_norm(x, epsilon = 1e-5);

	if is_act:
		if activation == "relu": x = tf.nn.relu(x, name = "relu");
		elif activation == "leaky_relu": x = tf.nn.leaky_relu(x, alpha = leak_param, name = "leaky_relu");
		elif activation == "elu": x = tf.nn.elu(x, name = "elu");
		elif activation == "tanh": x = tf.nn.tanh(x, name = "tanh");
		else: print("Check your Activation function")

	return x
  

def conv_2d_transpose(inp_ten, kernel_sz = 3, strides = 2, out_channels = 64, is_deconv = True, is_act = True, activation = "relu",
                      leak_param = 1/5.5, is_norm = True, normalization = "instance", is_dropout = False, use_bias = False):
    
    """
    Arguments:
    inp_ten:       Input Tensor
    kernel_sz:     Integer or tuple/list of 2 integers, specifying the height and width of the 2D convolution window
    strides:       Integer or tuple/list of 2 integers, specifying the strides of the convolution along the height and width
    out_channels:  Integer, the dimensionality of the output space
    is_conv:       Boolean, whether to perform convolution or not
    is_norm:       Boolean, whether to normalize the data or not
    normalization: Type of normalization, supports batch and instance normalization
    is_act:        Boolean, whether to apply non-linear activation functions or not
    activation:    Type of activation function, supports Leaky_ReLU, ReLU and Elu
    leak_param:    Integer, Leakiness to use in case of Leaky ReLU
    padding:       "Valid" (Reflection padding) or "SAME"(Constant padding filled with 0s)
    use_bias:      Boolean, whether to use bias or not
    is_dropout:    Boolean, whether to use dropout or not
    
    Returns:
    x:             Output Tensor
    """

    if is_deconv:
        x = tf.layers.conv2d_transpose(inputs = inp_ten, filters = out_channels, kernel_size = kernel_sz, strides = strides, padding = "SAME",
                      use_bias = use_bias, kernel_initializer = tf.random_normal_initializer(mean = 0, stddev = 0.02, dtype = tf.float32));
    
    if is_norm:
        if normalization == "batch": x = tf.layers.batch_normalization(x, momentum = 0.9, epsilon = 1e-6, training = train_mode);
        elif normalization == "instance": x = tf.contrib.layers.instance_norm(x, epsilon = 1e-5);
            
    if is_act:
        if activation == "relu": x = tf.nn.relu(x, name = "relu");
        elif activation == "leaky_relu": x = tf.nn.leaky_relu(x, alpha = leak_param, name = "leaky_relu");
        elif activation == "elu": x = tf.nn.elu(x, name = "elu");
        elif activation == "tanh": x = tf.nn.tanh(x, name = "tanh");
        else: print("Check your Activation function")
            
    if is_dropout: x = tf.nn.dropout(x, keep_prob = (1 - dropout))
            
    return x


def res_blk(inp_ten, kernel_sz = 3, strides = 1, out_channels = 256, name = None):
    
    """
    Arguments:
    inp_ten:       Input tensor
    kernel_sz:     Integer or tuple/list of 2 integers, specifying the height and width of the 2D convolution window
    strides:       Integer or tuple/list of 2 integers, specifying the strides of the convolution along the height and width
    out_channels:  Number of output filters in convolutional layer
    name:          Name to be used inside variable scope 
    
    Returns:
    output:       Output tensor
    """

    with tf.variable_scope(name):
        
        x = conv_2d(inp_ten, kernel_sz = kernel_sz, strides = strides, out_channels = out_channels, padding = "VALID");
        x = conv_2d(x, kernel_sz = kernel_sz, strides = strides, out_channels = out_channels, is_act = False, padding = "VALID")
        
        return x + inp_ten;

def Generator(inp_ten, out_channels = 64, name = None, reuse = False):

    """
    Arguments:
    inp_ten:       Input tensor
    out_channels:  Number of output filters in convolutional layer
    name:          Name to be used inside variable scope 
    reuse:         Boolean, whether to reuse the variables of the network or not
    
    Returns:
    output:       Output tensor
    """
    
    with tf.variable_scope(name, reuse = reuse):
        
        with tf.variable_scope("Block_1"):
        	# First layer with kernel size of 7, and reflection padding (to avoid checkerboard artifacts)
            x = conv_2d(inp_ten, kernel_sz = 7, strides = 1, out_channels = out_channels*1, padding = "VALID");
            # Downsample the original image 
            x = conv_2d(x, kernel_sz = 3, strides = 2, out_channels = out_channels*2, padding = "VALID"); 
            x = conv_2d(x, kernel_sz = 3, strides = 2, out_channels = out_channels*4, padding = "VALID"); 

        # Apply the resblocks on the downsampled image 
        with tf.variable_scope("Block_2"):
            for i in range(9): x = res_blk(x, 3, 1, out_channels*4, name = "ResBlk_" + str(i));

        with tf.variable_scope("Block_3"):
        	# Apply conv2d_transpose to upsample the image back to original dimensions
            x = conv_2d_transpose(x, kernel_sz = 3, strides = 2, out_channels = out_channels*2);
            x = conv_2d_transpose(x, kernel_sz = 3, strides = 2, out_channels = out_channels*1);
            # Last layer with no normalization, kernel size of 7, and tanh activation function
            x = conv_2d(x, kernel_sz = 7, strides = 1, out_channels = 3, activation = "tanh", is_norm = False, padding = "VALID");

        return x;


def Discriminator(inp_ten, out_channels = 64, use_sigmoid = False, name = None, reuse = False):

    """
    Arguments:
    inp_ten:       Input tensor
    out_channels:  Number of output filters in convolutional layer
    name:          Name to be used inside variable scope 
    reuse:         Boolean, whether to reuse the variables of the network or not
    use_sigmoid:   Boolean, whether to use sigmoid at the last layer

    Returns:
    output:       Output tensor
    """
    
    # Patch GAN with 70*70 receptive field
    with tf.variable_scope(name, reuse = reuse):
        
        # Stride 2 convolution, and "Same" padding 
        with tf.variable_scope("Block_1"):
        	# No normalization at the first layer
            x = conv_2d(inp_ten, kernel_sz = 4, strides = 2, out_channels = out_channels, is_norm = False, activation = "leaky_relu")

        with tf.variable_scope("Block_2"):
            for i in range(1, 4): x = conv_2d(x, kernel_sz = 4, strides = 2, out_channels = out_channels*min(2**i, 8),
                                              activation = "leaky_relu");

        # Stride 1 convolution, and "Same" padding 
        with tf.variable_scope("Block_3"):
            x = conv_2d(x, kernel_sz = 4, strides = 1, out_channels = 1, is_norm = False, is_act = False, use_bias = True)

        # use sigmoid only if the loss function is Cross-entropy (here we are using LS-GAN loss)
        if use_sigmoid == True:
            x = tf.nn.sigmoid(x); print('Sigmoid activation in the discriminator')

        return x


def fake_image_pool(num_fakes, fake, fake_pool):
    
    """
    Arguments:
    num_fakes: Number of fake images generated till now
    fake_img:  Fake image generated by Generator
    fake_pool: Array to store those fake images

    Returns:
    fake:      Fake Image to be used to update the weights of the discriminator 
    """

	if(num_fakes < pool_size): fake_pool[num_fakes] = fake; return fake
	else:
		p = random.random();
		if p > 0.5: 
			random_id = random.randint(0, pool_size-1); temp = fake_pool[random_id];
			fake_pool[random_id] = fake; return temp;
		else: return fake

def get_loss(real_prob, fake_prob, fake_pool_prob):
    
    """
    Arguments:
    real_prob:      Probability of the real image
    fake_prob:      Probability of the fake image
    fake_pool_prob: Probability of the image selected randomly from the pool
    
    Returns:
    g_loss:         Generator loss
    d_loss:         Discriminator loss
    """

    # LS-GAN loss
    with tf.variable_scope("Loss"):
      
        g_loss =  tf.reduce_mean(tf.squared_difference(fake_prob, 1));
        d_loss =  tf.reduce_mean(tf.squared_difference(real_prob, 1)); 
        d_loss += tf.reduce_mean(tf.square(fake_pool_prob)); d_loss *= 0.5;
        
        return g_loss, d_loss

def get_optimizer(loss, var_list):

    """
    Arguments:
    loss:          Loss to be minimized
    var_list:      List of the variables to be optimized

    Returns:
    learning_step: Train_op of the network
    """
	
	global_step = tf.Variable(0, trainable = False); starter_learning_rate = 2e-4; end_learning_rate = 0.0;
	start_decay_step = 100000; decay_steps = 100000; beta1 = 0.5;

	# Constant learning rate till 100 epochs, after that linearly decrease it to 0
	learning_rate = (tf.where(tf.greater_equal(global_step, start_decay_step), tf.train.polynomial_decay(starter_learning_rate, 
			 global_step - start_decay_step, decay_steps, end_learning_rate, power = 1.0), starter_learning_rate));

    # Define the Adam optimizer with the non-default beta1
	learning_step = tf.train.AdamOptimizer(learning_rate, beta1 = beta1).minimize(loss, global_step = global_step, 
										      var_list = var_list);
	
	return learning_step;


def initialize_model(lambda_1 = 10, lambda_2 = 0.5):

	"""
    Arguments:
    lambda_1: Coef of the Cycle Loss 
    lambda_2: Coef of the Identity loss
    """
    
	global input_a, input_b, fake_pool_a, fake_pool_b, train_mode, dropout, lr;

	# Define the placeholders
	with tf.name_scope("Place_holders"):
		input_a = tf.placeholder(dtype = tf.float32, shape = [None, img_height, img_width, img_channels], name = "Img_A");
		input_b = tf.placeholder(dtype = tf.float32, shape = [None, img_height, img_width, img_channels], name = "Img_B");
		fake_pool_a = tf.placeholder(tf.float32, shape = [None, img_height, img_width, img_channels], name = "Fake_pool_A");
		fake_pool_b = tf.placeholder(tf.float32, shape = [None, img_height, img_width, img_channels], name = "Fake_pool_B");
		dropout = tf.placeholder(dtype = tf.float32, name = "Dropout"); train_mode = tf.placeholder(dtype = tf.bool);

	fake_b  = Generator(inp_ten = input_a, name = "Generator_a2b", reuse = False);
	recon_a = Generator(inp_ten = fake_b,  name = "Generator_b2a", reuse = False);
	fake_a  = Generator(inp_ten = input_b, name = "Generator_b2a", reuse = True);
	recon_b = Generator(inp_ten = fake_a,  name = "Generator_a2b", reuse = True);

	# Fake Image generated by both the Generators for the Identity loss
	fake_b_ = Generator(inp_ten = input_b, name = "Generator_a2b", reuse = True);
	fake_a_ = Generator(inp_ten = input_a, name = "Generator_b2a", reuse = True);

	real_prob_a = Discriminator(inp_ten = input_a, name = "Discriminator_a", reuse = False);
	fake_prob_a = Discriminator(inp_ten = fake_a,  name = "Discriminator_a", reuse = True);
	real_prob_b = Discriminator(inp_ten = input_b, name = "Discriminator_b", reuse = False);
	fake_prob_b = Discriminator(inp_ten = fake_b,  name = "Discriminator_b", reuse = True);

	# Probabilities  outputted by the Discriminator corresponding to the fake image pool
	fake_prob_pool_a = Discriminator(fake_pool_a,  name = "Discriminator_a", reuse = True);
	fake_prob_pool_b = Discriminator(fake_pool_b,  name = "Discriminator_b", reuse = True); 

	update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
	with tf.control_dependencies(update_ops):

		# Get the Loss
		g_b2a_loss, d_a_loss = get_loss(real_prob_a, fake_prob_a, fake_prob_pool_a); 
		g_a2b_loss, d_b_loss = get_loss(real_prob_b, fake_prob_b, fake_prob_pool_b);

		# Cycle Consistency and Identity Loss
		cycle_consistency_loss = lambda_1*(tf.reduce_mean(tf.abs(input_a - recon_a)) + tf.reduce_mean(tf.abs(input_b - recon_b)));
		identity_loss = lambda_1*lambda_2*(tf.reduce_mean(tf.abs(input_a - fake_a_)) + tf.reduce_mean(tf.abs(input_b - fake_b_)));

		# Net Loss of both the generators
		g_b2a_loss = g_b2a_loss + cycle_consistency_loss + identity_loss; 
		g_a2b_loss = g_a2b_loss + cycle_consistency_loss + identity_loss;

		# Seperate out the variables of each network
		d_a_vars = [var for var in tf.trainable_variables() if "Discriminator_a" in var.name]
		d_b_vars = [var for var in tf.trainable_variables() if "Discriminator_b" in var.name]
		g_b2a_vars = [var for var in tf.trainable_variables() if "Generator_b2a" in var.name]
		g_a2b_vars = [var for var in tf.trainable_variables() if "Generator_a2b" in var.name]

		# Define the train_ops
		d_a_train_op   = get_optimizer(d_a_loss, var_list = d_a_vars); g_b2a_train_op = get_optimizer(g_b2a_loss, var_list = g_b2a_vars)
		d_b_train_op   = get_optimizer(d_b_loss, var_list = d_b_vars); g_a2b_train_op = get_optimizer(g_a2b_loss, var_list = g_a2b_vars)

		return fake_b, recon_a, fake_a, recon_b, d_a_loss, d_a_train_op, d_b_loss, d_b_train_op, g_b2a_loss, g_b2a_train_op, g_a2b_loss, g_a2b_train_op;

def show_images(image_batch, tmp_path = None, show = False, save = True, id = None, **kwargs):

	# Helper function to show some nice plots

	image_batch = (image_batch + 1)*0.5; img_index = 1; fig = plt.figure(figsize = (14, 8), **kwargs); 
	for _ in range(2):
		for _ in range(3):
			fig.add_subplot(2, 3, img_index); plt.imshow(image_batch[img_index - 1], cmap = 'binary'); 
			plt.gca().set_xticks([]); plt.gca().set_yticks([]); img_index += 1;
			
	if not os.path.exists(tmp_path): os.makedirs(tmp_path);
	plt.savefig(os.path.join(tmp_path, '{}.png'.format(id))); plt.close()

def train(num_epochs, num_iters):
    
	g_train = tf.get_default_graph();
	with g_train.as_default():
        
		tf.set_random_seed(0); num_fake_imgs = 0;
		with tf.Session(graph = g_train) as sess:
            
			fake_b, recon_a, fake_a, recon_b, d_a_loss, d_a_train_op, d_b_loss, d_b_train_op, g_b2a_loss, g_b2a_train_op, \
                                                                                g_a2b_loss, g_a2b_train_op = initialize_model();
            
			handle, next_element, mon_iterator, mon_handle, cez_iterator, cez_handle = get_iterators(sess);
			sess.run(tf.global_variables_initializer()); sess.run(mon_iterator.initializer); sess.run(cez_iterator.initializer); 
			print("Training Started..."); tot_D_A_Loss = tot_G_A_loss = tot_D_B_Loss = tot_G_B_Loss = 0;

			for iters in range(1, num_epochs*num_iters):

				try: img_a = sess.run(next_element, feed_dict = {handle: mon_handle});
				except tf.errors.OutOfRangeError: sess.run(mon_iterator.initializer);

				try: img_b = sess.run(next_element, feed_dict = {handle: cez_handle})
				except tf.errors.OutOfRangeError: sess.run(cez_iterator.initializer); 

				if img_a.shape[-1] != 3 or img_b.shape[-1] != 3: continue;

				# Update Generator and Discriminator alternately (Start with the Generator) 
				_, Fake_A, G_A_loss = sess.run([g_b2a_train_op, fake_a, g_b2a_loss], feed_dict = {input_a: img_a, 
								input_b: img_b, train_mode: True, dropout: 0})
				
				Fake_pool_A = fake_image_pool(num_fake_imgs, Fake_A, fake_a_arr);
				_, D_A_Loss = sess.run([d_a_train_op, d_a_loss], feed_dict = {input_a: img_a, input_b: img_b, 
							fake_pool_a: Fake_pool_A, train_mode: True, dropout: 0})
				
				_, Fake_B, G_B_Loss = sess.run([g_a2b_train_op, fake_b, g_a2b_loss], feed_dict = {input_a: img_a, 
								input_b: img_b, train_mode: True, dropout: 0})
				
				Fake_pool_B = fake_image_pool(num_fake_imgs, Fake_B, fake_b_arr);
				_, D_B_Loss = sess.run([d_b_train_op, d_b_loss], feed_dict = {input_a: img_a, input_b: img_b, 
							fake_pool_b: Fake_pool_B, train_mode: True, dropout: 0})

				# Gather some Statistics
				tot_D_A_Loss += D_A_Loss; tot_G_A_loss += G_A_loss; 
				tot_D_B_Loss += D_B_Loss; tot_G_B_Loss += G_B_Loss; 
				num_fake_imgs += 1;

				if iters%num_iters == 0:

					Fake_img_B  = sess.run(fake_b, feed_dict = {input_a: img_a, train_mode: True, dropout: 0});
					Fake_img_A  = sess.run(fake_a, feed_dict = {input_b: img_b, train_mode: True, dropout: 0});

					Recon_img_B = sess.run(recon_b, feed_dict = {input_b: img_b, train_mode: True, dropout: 0});
					Recon_img_A = sess.run(recon_a, feed_dict = {input_a: img_a, train_mode: True, dropout: 0});

					image_batch = np.concatenate((img_a, Fake_img_B, Recon_img_A, img_b, Fake_img_A, Recon_img_B)); 
					show_images(image_batch, tmp_path = "./CycleGAN/", id = iters);

					print('After ' + str(iters)+ ': D_A_Loss: ' + str(tot_D_A_Loss/iters) + ', D_B_Loss: ' + \
					      str(tot_D_B_Loss/iters) + ', G_B2A_loss: ' + str(tot_G_A_loss/iters) + ', G_A2B_Loss: ' + \
					      str(tot_G_B_Loss/iters));
					
	tf.reset_default_graph(); return;

tf.get_default_graph(); train(200, min(len(mon_file_name), len(cez_file_name)));

