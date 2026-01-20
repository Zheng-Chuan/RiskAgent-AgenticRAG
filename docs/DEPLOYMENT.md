# DEPLOYMENT

## 目标

把开发期中间件配置和偏生产的配置拆开
避免修改deploy配置时影响日常开发

## Dev Compose

- 文件: deploy/dev/docker-compose.yml
- 用途: 本地开发快速启动Milvus

启动

```bash
docker compose -f deploy/dev/docker-compose.yml up -d
```

## Prod Like Compose

- 文件: deploy/prod/docker-compose.yml
- 用途: 提供一个更接近长期运行的compose模板
- 差异: 默认restart unless-stopped

启动

```bash
docker compose -f deploy/prod/docker-compose.yml up -d
```

