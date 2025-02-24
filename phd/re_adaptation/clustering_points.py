import random
import math

# Function to calculate Euclidean distance
def euclidean_distance(point1, point2):
    return math.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)

# Function to calculate the percentage of points close to A
def calculate_percentage_close(points, A, threshold):
    close_count = sum(1 for point in points if euclidean_distance(point, A) <= threshold)
    percentage = (close_count / len(points)) * 100
    return percentage

# Generate 30 random points (x, y)
random_points = [(random.uniform(0, 100), random.uniform(0, 100)) for _ in range(100)]

# List of workers and their points
list_with_workers = ["worker_1", "worker_2", "worker_3"]
points_of_workers = [(10, 30), (50, 50), (60, 70)]

# Define the distance threshold
threshold = 20  # You can adjust this value

def get_proximity_per_worker(list_with_workers:list, points_of_workers:list, user_points):
    list_with_proximities_per_worker = []
    for worker, point in zip(list_with_workers, points_of_workers):
        list_with_proximities_per_worker.append((worker, calculate_percentage_close(user_points, point, threshold)))
    return list_with_proximities_per_worker

print(get_proximity_per_worker(list_with_workers, points_of_workers, random_points))


