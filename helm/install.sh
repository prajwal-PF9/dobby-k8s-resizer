#!/bin/bash
# Install VPA + Goldilocks into the cluster and label target namespaces.
# Run this ONCE before deploying hack-resizer.
set -e

echo "==> Adding Fairwinds Helm repo..."
helm repo add fairwinds-stable https://charts.fairwinds.com/stable
helm repo update

echo "==> Installing VPA (recommendation-only mode)..."
helm upgrade --install vpa fairwinds-stable/vpa \
  --namespace vpa-system \
  --create-namespace \
  --set recommender.enabled=true \
  --set updater.enabled=false \
  --set admissionController.enabled=false

echo "==> Installing Goldilocks..."
helm upgrade --install goldilocks fairwinds-stable/goldilocks \
  --namespace goldilocks \
  --create-namespace

echo "==> Labeling target namespaces for Goldilocks..."
kubectl label namespace prajwal-hack goldilocks.fairwinds.com/enabled=true --overwrite
kubectl label namespace prajwal-hack-region-1 goldilocks.fairwinds.com/enabled=true --overwrite

echo "==> Done."
echo "    Dashboard: kubectl -n goldilocks port-forward svc/goldilocks-dashboard 8080:80"
