# Kubernetes Basics

## What is Kubernetes?

Kubernetes (K8s) is an open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications. Originally developed by Google, it is now maintained by the Cloud Native Computing Foundation (CNCF).

Kubernetes groups containers into logical units called Pods. A Pod is the smallest deployable unit in Kubernetes and can contain one or more containers that share storage and network resources.

## Core Components

### Control Plane

The control plane manages the overall state of the cluster:

- **kube-apiserver**: The API server exposes the Kubernetes API. It is the front end for the Kubernetes control plane.
- **etcd**: A consistent and highly-available key-value store used as Kubernetes' backing store for all cluster data.
- **kube-scheduler**: Watches for newly created Pods with no assigned node and selects a node for them to run on.
- **kube-controller-manager**: Runs controller processes including the node controller, replication controller, endpoints controller, and service account controller.

### Worker Nodes

Each worker node contains:

- **kubelet**: An agent that runs on each node and ensures containers are running in a Pod.
- **kube-proxy**: A network proxy that maintains network rules on nodes, allowing network communication to Pods.
- **Container Runtime**: Software responsible for running containers (e.g., containerd, CRI-O).

## Key Concepts

### Deployments

A Deployment provides declarative updates for Pods and ReplicaSets. You describe a desired state in a Deployment, and the Deployment controller changes the actual state to the desired state at a controlled rate.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
```

### Services

A Service is an abstraction that defines a logical set of Pods and a policy to access them. Services enable network access to a set of Pods. Types include ClusterIP, NodePort, LoadBalancer, and ExternalName.

### ConfigMaps and Secrets

ConfigMaps allow you to decouple configuration artifacts from container images. Secrets are similar but designed to hold sensitive information like passwords and API keys.

### Namespaces

Namespaces provide a mechanism for isolating groups of resources within a single cluster. They are intended for use in environments with many users spread across multiple teams.

## Common kubectl Commands

```bash
# Get cluster info
kubectl cluster-info

# List all pods
kubectl get pods --all-namespaces

# Create a deployment
kubectl create deployment nginx --image=nginx

# Scale a deployment
kubectl scale deployment nginx --replicas=5

# Expose a deployment
kubectl expose deployment nginx --port=80 --type=LoadBalancer

# Get logs
kubectl logs <pod-name>

# Execute command in pod
kubectl exec -it <pod-name> -- /bin/bash
```

<details><summary>What is a Pod in Kubernetes?</summary><br><b>A Pod is the smallest deployable unit in Kubernetes. It represents a single instance of a running process and can contain one or more containers that share storage and network resources.</b></details>

<details><summary>What does the kube-scheduler do?</summary><br><b>The kube-scheduler watches for newly created Pods that have no assigned node and selects a node for them to run on based on resource requirements, constraints, and other factors.</b></details>

<details><summary>What is a Kubernetes Service?</summary><br><b>A Service is an abstraction that defines a logical set of Pods and a policy to access them, enabling network access. Service types include ClusterIP, NodePort, LoadBalancer, and ExternalName.</b></details>
