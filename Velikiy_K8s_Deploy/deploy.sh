#!/bin/bash
set -e

echo "🚀 Starting full deployment..."

# 1. Build and push Docker image
echo "📦 Building Docker image..."
cd app
docker build -t gleb1337/velikiy-app:latest .
docker push gleb1337/velikiy-app:latest
cd ..

# 2. Run Ansible playbook
echo "🔧 Running Ansible playbook..."
cd ansible
ansible-playbook -i inventory.ini playbook.yml
cd ..

# 3. Deploy Helm charts via ArgoCD
echo "📊 Deploying to ArgoCD..."
kubectl apply -f argocd/applications/

# 4. Wait for applications
echo "⏳ Waiting for applications to sync..."
sleep 120

# 5. Verify
echo "✅ Verifying deployment..."
kubectl get pods -A
kubectl get svc -A

echo ""
echo "🎉 Deployment complete!"
echo "📱 App: http://192.168.122.75:30030"
echo "📊 Grafana: http://192.168.122.75:30030 (admin/admin123)"
echo "🔍 ArgoCD: kubectl port-forward svc/argocd-server -n argocd 8080:443"