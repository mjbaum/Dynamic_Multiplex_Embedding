from .helpers import generate_adjacency_matrix, get_embedding, generate_group_labels, group_by_label
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
import pylab as py
from scipy.linalg import orthogonal_procrustes

class dmpsbm:

    # Initialize the model with the number of layers, timesteps, groups, and the dictionary of probabilities
    def __init__(self, layers, timesteps, groups, prob_dict):
        # Store the model parameters (after checking that they are valid)
        if not isinstance(layers, int) or layers <= 0:
            raise ValueError("The number of layers must be a positive integer")
        self.layers = layers
        if not isinstance(timesteps, int) or timesteps <= 0:
            raise ValueError("The number of timesteps must be a positive integer")
        self.timesteps = timesteps
        if not isinstance(groups, list) or len(groups) == 0 or not all(isinstance(x, int) for x in groups):
            raise ValueError("The groups must be a non-empty list of integers")
        self.groups = groups
        if not isinstance(prob_dict, dict) or not all(isinstance(key, tuple) and len(key) == 2 and isinstance(value, list) for key, value in prob_dict.items()):
            raise ValueError("The probability dictionary must be a dictionary with keys as tuples and values as lists")
        self.prob_dict = prob_dict
        # Initialize other model attributes to None
        self.A = None
        self.left_embedding = None
        self.right_embedding = None
        self.left_centroids = None
        self.right_centroids = None
        self.left_embedding_theo = None
        self.right_embedding_theo = None
        self.rotation_left = None
        self.rotation_right = None
        self.error = 0

    # Sample the adjacency matrices and calculate the embeddings
    def sample(self):
        list_longs = []
        for i in range(self.layers):
            curr_long = []
            for j in range(self.timesteps):
                curr_A = generate_adjacency_matrix(len_groups=self.groups, probabilities=self.prob_dict[(i, j)])
                curr_long.append(curr_A)
            final_long = np.concatenate(curr_long, axis=1)
            list_longs.append(final_long)
        final_embedding = np.concatenate(list_longs, axis=0)
        self.A = final_embedding
        left_embedding = get_embedding(final_embedding, type='left')
        self.left_embedding = left_embedding
        right_embedding = get_embedding(final_embedding, type='right')
        self.right_embedding = right_embedding

    # Calculate the theoretical embeddings and rotate them to match the sampled embeddings
    def get_centroids_theo(self):
        list_longs = []
        for i in range(self.layers):
            curr_long = []
            for j in range(self.timesteps):
                curr_B = self.prob_dict[(i, j)]
                curr_long.append(curr_B)
            final_long = np.concatenate(curr_long, axis=1)
            list_longs.append(final_long)
        final_embedding = np.concatenate(list_longs, axis=0)
        self.left_embedding_theo = get_embedding(final_embedding, type='left')
        self.right_embedding_theo = get_embedding(final_embedding, type='right')
        self.rotate()

    # Calculate the rotation matrices to align the theoretical embeddings with the sampled embeddings
    def get_rotation(self):
        left_stacked = np.concatenate(self.left_centroids, axis = 0)
        rotation = orthogonal_procrustes(self.left_embedding_theo, left_stacked)[0]
        self.rotation_left = rotation
        right_stacked = np.concatenate(self.right_centroids, axis=0)
        rotation = orthogonal_procrustes(self.right_embedding_theo, right_stacked)[0]
        self.rotation_right = rotation

    # Rotate the theoretical embeddings to match the sampled embeddings
    def rotate(self):
        self.get_rotation()
        self.left_embedding_theo = self.left_embedding_theo @ self.rotation_left
        self.right_embedding_theo = self.right_embedding_theo @ self.rotation_right
        self.calculate_error()
        print("Total Error: ", self.error)

    # Calculate the error between the sampled and theoretical embeddings
    def calculate_error(self):
        left_stacked = np.concatenate(self.left_centroids, axis=0)
        right_stacked = np.concatenate(self.right_centroids, axis=0)
        self.error = sum(sum((self.left_embedding_theo - left_stacked)**2)) + sum(sum((self.right_embedding_theo - right_stacked)**2))
        self.calculate_variance()

    # Calculate the variance of the embeddings within each community
    def calculate_variance(self):
        num_nodes = sum(self.groups)
        for layer in range(self.layers):
            current_layer = self.left_embedding[num_nodes*layer:num_nodes*(layer+1), :]
            start = 0
            variances = []
            for size in self.groups:
                variances.append(sum(np.var(current_layer[start:start + size, :], axis=0)))
                start += size
            plt.bar(x = range(len(self.groups)), height = variances, color = 'darkblue')
            plt.title("Community Variances Layer " + str(layer+1))
            plt.show()
        for time in range(self.timesteps):
            current_time = self.right_embedding[num_nodes*time:num_nodes*(time+1), :]
            start = 0
            variances = []
            for size in self.groups:
                variances.append(sum(np.var(current_time[start:start + size, :], axis=0)))
                start += size
            plt.bar(x = range(len(self.groups)), height = variances, color = 'darkblue')
            plt.title("Community Variances Time " + str(time+1))
            plt.show()

    # Calculate the centroids of the communities in the embeddings
    def get_centroids(self):
        left_centroids = []
        right_centroids = []
        total_nodes = sum(self.groups)
        for layer in range(self.layers):
            current_layer = self.left_embedding[total_nodes*layer:total_nodes*(layer+1), :]
            current_embeddings = []
            for label in set(generate_group_labels(len_groups=self.groups)):
                labels = np.array(generate_group_labels(len_groups=self.groups))
                community = current_layer[labels == label]
                current_embeddings.append([np.mean(community[:, 0]), np.mean(community[:, 1]), np.mean(community[:, 2]), np.mean(community[:, 3])])
            left_centroids.append(current_embeddings)
        self.left_centroids = left_centroids
        for time in range(self.timesteps):
            current_time = self.right_embedding[total_nodes*time:total_nodes*(time+1), :]
            current_embeddings = []
            for label in set(generate_group_labels(len_groups=self.groups)):
                labels = np.array(generate_group_labels(len_groups=self.groups))
                community = current_time[labels == label]
                current_embeddings.append([np.mean(community[:, 0]), np.mean(community[:, 1]), np.mean(community[:, 2]), np.mean(community[:, 3])])
            right_centroids.append(current_embeddings)
        self.right_centroids = right_centroids

    # Plot the embeddings and centroids
    def plot(self):
        total_nodes  = sum(self.groups)
        num_groups = len(self.groups)
        for layer in range(self.layers):
            fig, ax = plt.subplots()
            ax.grid()
            ax.scatter(x=self.left_embedding[total_nodes*layer:total_nodes*(layer+1), 0], y=self.left_embedding[total_nodes*layer:total_nodes*(layer+1), 1], c=generate_group_labels(len_groups=self.groups))
            ax.scatter(x=self.left_embedding_theo[num_groups * layer:num_groups * (layer + 1), 0], y=self.left_embedding_theo[num_groups * layer:num_groups * (layer + 1), 1], c='orange', marker='x', s=80)
            for point in self.left_centroids[layer]:
                ax.scatter(point[0], point[1], c='red')
            plt.title("Left Embedding Layer " + str(layer+1))
            plt.show()
        for time in range(self.timesteps):
            fig, ax = plt.subplots()
            ax.grid()
            ax.scatter(x=self.right_embedding[total_nodes*time:total_nodes*(time+1), 0], y=self.right_embedding[total_nodes*time:total_nodes*(time+1), 1], c=generate_group_labels(len_groups=self.groups))
            ax.scatter(x=self.right_embedding_theo[num_groups * time:num_groups * (time + 1), 0], y=self.right_embedding_theo[num_groups * time:num_groups * (time + 1), 1], c='orange', marker='x', s=80)
            for point in self.right_centroids[time]:
                ax.scatter(point[0], point[1], c='red')
            plt.title("Right Embedding Time " + str(time+1))
            plt.show()

    # Generate a QQ plot for the embeddings (marginally for each dimension)
    def qq_plot(self):
        num_nodes = sum(self.groups)
        for layer in range(self.layers):
            current_layer = self.left_embedding[num_nodes * layer:num_nodes * (layer + 1), :]
            start = 0
            for size in self.groups:
                community = current_layer[start:start + size, :]
                mean = np.mean(community, axis=0)
                community = community - mean
                for dimension in range(4):
                    sm.qqplot(community[:, dimension], fit=True, line=45)
                    py.show()
                start += size