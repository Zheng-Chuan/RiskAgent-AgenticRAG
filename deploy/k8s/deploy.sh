#!/bin/bash
# RiskAgent-AgenticRAG k8s 部署脚本
# 用法: ./deploy/k8s/deploy.sh [build|apply|all]

set -e

NAMESPACE="riskagent"
K8S_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$K8S_DIR/../.." && pwd)"

ACTION="${1:-all}"

# 构建镜像
build_image() {
    echo "==== 构建 Docker 镜像 ===="
    cd "$PROJECT_ROOT"
    docker build -t riskagent-agenticrag:latest .
    echo "==== 镜像构建完成 ===="
}

# 部署到 k8s
apply_manifests() {
    echo "==== 部署 k8s manifests ===="
    kubectl apply -f "$K8S_DIR/00-namespace.yaml"
    kubectl apply -f "$K8S_DIR/01-configmap.yaml"
    kubectl apply -f "$K8S_DIR/02-secret.yaml"
    kubectl apply -f "$K8S_DIR/10-milvus.yaml"
    kubectl apply -f "$K8S_DIR/20-redis.yaml"
    kubectl apply -f "$K8S_DIR/30-app.yaml"
    echo "==== k8s manifests 部署完成 ===="
}

# 等待所有 pod 就绪
wait_pods() {
    echo "==== 等待 Pod 就绪 ===="
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=milvus -n "$NAMESPACE" --timeout=180s || true
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=redis -n "$NAMESPACE" --timeout=60s || true
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=riskagent-api -n "$NAMESPACE" --timeout=180s || true
    echo "==== Pod 状态 ===="
    kubectl get pods -n "$NAMESPACE"
}

# 显示服务状态
show_status() {
    echo "==== 服务状态 ===="
    kubectl get svc -n "$NAMESPACE"
    echo ""
    echo "==== Pod 状态 ===="
    kubectl get pods -n "$NAMESPACE"
    echo ""
    echo "==== 访问方式 ===="
    echo "API: http://localhost:30800/healthz"
    echo "Metrics: http://localhost:30800/metrics"
    echo "API Key: riskagent-k8s-api-key"
}

case "$ACTION" in
    build)
        build_image
        ;;
    apply)
        apply_manifests
        wait_pods
        show_status
        ;;
    all)
        build_image
        apply_manifests
        wait_pods
        show_status
        ;;
    status)
        show_status
        ;;
    *)
        echo "用法: $0 [build|apply|all|status]"
        exit 1
        ;;
esac
