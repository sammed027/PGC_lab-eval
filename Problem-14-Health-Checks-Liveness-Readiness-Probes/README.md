# Problem 14: Kubernetes Health Checks with Liveness and Readiness Probes

**Experiment:** Deploy a containerized Flask application to Kubernetes and observe how liveness and readiness probes affect container recovery and Service traffic.

## 1. Aim

To understand and implement Kubernetes health monitoring using HTTP liveness and readiness probes, and to observe the different actions Kubernetes takes when an application becomes unhealthy or temporarily unable to accept traffic.

## 2. Learning objectives

- Build and run a small Flask application inside a Docker container.
- Create a Kubernetes Deployment with two replicas.
- Configure HTTP liveness and readiness probes.
- Observe pod readiness, container restart counts, and Service endpoints.
- Simulate failures and restore the application.
- Distinguish a process that must be restarted from a process that should temporarily stop receiving traffic.

## 3. Requirements

- Docker Desktop or Docker Engine
- Kubernetes cluster (Kind is suitable for this experiment)
- kubectl
- Python 3.12 (only needed for running the application outside Docker)
- Flask 3.1.2

## 4. Concepts

### Liveness probe

A liveness probe answers: **Is the application process still healthy enough to continue running?**

Kubernetes periodically calls the configured endpoint. When the number of consecutive failures reaches `failureThreshold`, Kubernetes restarts the container. This is useful when an application is stuck or cannot recover by itself.

### Readiness probe

A readiness probe answers: **Should this pod receive application traffic right now?**

When readiness fails, Kubernetes marks the pod as not ready and removes it from the eligible Service backends. The container is not restarted just because readiness fails. When the check succeeds again, the pod can receive traffic.

### Why both are needed

A process can be alive while it is still starting up or unable to serve requests. In that situation, liveness can pass while readiness fails. Keeping these checks separate prevents unnecessary restarts during temporary unavailability.

## 5. Project structure

```text
Problem-14-Health-Checks-Liveness-Readiness-Probes/
├── app.py
├── requirements.txt
├── Dockerfile
├── deployment.yaml
├── service.yaml
└── README.md
```

## 6. Application endpoints

| Method | Endpoint | Purpose | Expected result when healthy |
|---|---|---|---|
| GET | `/` | Application information | HTTP 200 |
| GET | `/live` | Liveness check | `Alive`, HTTP 200 |
| GET | `/ready` | Readiness check | `Ready`, HTTP 200 |
| POST | `/fail-liveness` | Simulate an unhealthy process | Liveness returns HTTP 500 |
| POST | `/fail-readiness` | Simulate temporary unavailability | Readiness returns HTTP 503 |
| POST | `/recover` | Restore both health flags | Both checks return HTTP 200 |

The failure flags are in-memory variables for demonstration. A container restart starts a fresh Python process and resets them to healthy.

## 7. Implementation

### Step 1: Create a Kubernetes cluster

For Kind, create a cluster if one is not already running:

```bash
kind create cluster --name health-lab
kubectl cluster-info
kubectl get nodes
```

### Step 2: Build the container image

Run these commands from this experiment directory:

```bash
docker build -t health-probe-demo:v1 .
```

For a Kind cluster, load the image into its nodes:

```bash
kind load docker-image health-probe-demo:v1 --name health-lab
```

### Step 3: Create the namespace

```bash
kubectl create namespace probe-lab
```

If it already exists, continue to the next step.

### Step 4: Deploy the application

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

### Step 5: Verify the deployment

```bash
kubectl get deployments -n probe-lab
kubectl get pods -n probe-lab -o wide
kubectl get services -n probe-lab
kubectl rollout status deployment/health-probe-app -n probe-lab
```

Expected initial state: two pods become Running and Ready, and the Deployment reports two available replicas.

### Step 6: Access the application

Open a terminal and run:

```bash
kubectl port-forward service/health-probe-service 8081:80 -n probe-lab
```

In another terminal, test the endpoints:

```bash
curl http://127.0.0.1:8081/
curl http://127.0.0.1:8081/live
curl http://127.0.0.1:8081/ready
```

The Service may route each request to either replica. For failure demonstrations, use a port-forward directly to one pod.

## 8. Demonstration A: Readiness failure

1. List pods and choose one pod name:

```bash
kubectl get pods -n probe-lab
```

2. Forward a local port directly to that pod (replace the placeholder):

```bash
kubectl port-forward pod/<pod-name> 8082:8080 -n probe-lab
```

3. In a second terminal, enable readiness failure:

```bash
curl -X POST http://127.0.0.1:8082/fail-readiness
```

4. Observe pod readiness and Service backends:

```bash
kubectl get pods -n probe-lab
kubectl get endpointslices -n probe-lab
```

**Expected observation:** the selected pod changes to not-ready (for example, `0/1`) but remains Running. Its restart count should not increase because a readiness failure does not restart the container. It is excluded from the Service's ready backends. The other healthy replica remains available.

5. Recover the application:

```bash
curl -X POST http://127.0.0.1:8082/recover
kubectl get pods -n probe-lab
kubectl get endpointslices -n probe-lab
```

After the next successful readiness check, the pod should become Ready and return to the Service backends.

## 9. Demonstration B: Liveness failure

Use a direct pod port-forward as in Demonstration A. Make sure the selected pod is healthy before beginning.

1. Trigger liveness failure:

```bash
curl -X POST http://127.0.0.1:8082/fail-liveness
```

2. Watch the pod:

```bash
kubectl get pods -n probe-lab -w
```

3. After Kubernetes detects the configured consecutive failures, stop watching with Ctrl+C and inspect the pod:

```bash
kubectl get pods -n probe-lab
kubectl describe pod <pod-name> -n probe-lab
```

**Expected observation:** Kubernetes restarts the failing container after the liveness failure threshold is reached. The restart count increases. The new application process starts with its default healthy flags, then passes readiness checks.

## 10. Probe configuration

| Setting | Liveness | Readiness |
|---|---:|---:|
| HTTP path | `/live` | `/ready` |
| Container port | 8080 | 8080 |
| Initial delay | 5 seconds | 3 seconds |
| Probe period | 5 seconds | 3 seconds |
| Timeout | 2 seconds | 2 seconds |
| Failure threshold | 3 | 2 |

The values are lab settings chosen to make the behavior observable. Production applications should tune these values to match their startup and recovery characteristics.

## 11. Evidence and screenshots to capture

Add your own screenshots to this folder or a dedicated `screenshots/` subfolder. Capture actual terminal output from your run; do not use another person's screenshots as evidence.

Recommended screenshots:

1. Docker image build completed successfully.
2. Kubernetes nodes are Ready.
3. Deployment and two pods are running.
4. Service is created.
5. `/`, `/live`, and `/ready` return healthy responses.
6. Readiness failure: selected pod is not Ready while restart count stays unchanged.
7. EndpointSlices show only ready backends.
8. Readiness recovery: pod becomes Ready again.
9. Liveness failure and container restart count increases.
10. `kubectl describe pod` shows liveness probe events.

Suggested names: `01-docker-build.png`, `02-cluster-nodes.png`, `03-pods-ready.png`, `04-service.png`, `05-health-endpoints.png`, `06-readiness-failure.png`, `07-endpointslices.png`, `08-readiness-recovery.png`, `09-liveness-restart.png`, and `10-pod-events.png`.

## 12. Results and observations

Record what you actually observe during execution:

| Test | Expected behavior | Actual observation |
|---|---|---|
| Initial health | Both probes pass | Fill after execution |
| Readiness failure | Pod becomes not-ready; no restart | Fill after execution |
| Readiness recovery | Pod becomes ready again | Fill after execution |
| Liveness failure | Container restarts after threshold | Fill after execution |

Do not report the experiment as completed until you have run it and captured the corresponding screenshots.

## 13. Troubleshooting

- **ImagePullBackOff:** confirm the image was built and loaded into the same Kind cluster; verify the image name and tag match the Deployment.
- **Pods remain Pending:** inspect `kubectl describe pod <pod-name> -n probe-lab` and check cluster resources.
- **Probe failures:** verify the container listens on `0.0.0.0:8080` and that the configured paths are correct.
- **Port-forward fails:** confirm the pod or Service exists and is running; use the namespace flag.
- **No liveness restart yet:** allow enough time for the initial delay, probe period, and consecutive failure threshold.
- **No screenshots:** capture your own terminal evidence after each stage and commit the images alongside this README.

## 14. Conclusion

This experiment demonstrates Kubernetes application health monitoring through two independent HTTP probes. The readiness probe controls whether a pod is eligible to receive Service traffic, whereas the liveness probe detects an unhealthy container and causes Kubernetes to restart it after repeated failures. Together, they improve the reliability of applications running in a Kubernetes cluster.

## 15. Viva questions

**1. What is a Kubernetes probe?**  
A periodic check Kubernetes performs to understand the state of a container.

**2. What is the purpose of a liveness probe?**  
It detects a container that is unhealthy or stuck and can trigger a restart.

**3. What is the purpose of a readiness probe?**  
It determines whether a pod should receive traffic through a Service.

**4. Does a readiness failure restart a container?**  
No. It marks the pod as not ready and removes it from eligible Service backends.

**5. What happens after repeated liveness failures?**  
Kubernetes restarts the container according to the pod's restart policy.

**6. Can a container be live but not ready?**  
Yes. For example, it may be running while waiting for a dependency or completing initialization.

**7. Why use two replicas?**  
To demonstrate that a healthy replica can continue serving traffic while another replica is temporarily unready.

**8. Why use a pod-specific port-forward for failure testing?**  
It makes sure the test request reaches the intended pod instead of an arbitrary Service backend.

**9. What is the role of a Kubernetes Service?**  
It provides a stable network endpoint and routes traffic to eligible pods selected by labels.

**10. What is the difference between a liveness and readiness probe?**  
Liveness influences container restarts; readiness influences whether a pod receives traffic.

---

**Implementation note:** This is an independently written lab version based on the stated experiment topic. Validate the commands and add screenshots from your own cluster before submission.
