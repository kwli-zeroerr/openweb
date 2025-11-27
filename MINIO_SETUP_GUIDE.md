# MinIO 配置指南

## 为什么使用 MinIO？

### 当前本地存储的局限性
- ✅ 简单直接，无需额外服务
- ❌ 单服务器限制，无法多服务器共享
- ❌ 备份需要手动操作
- ❌ 文件量大时管理困难
- ❌ 服务器磁盘故障会导致数据丢失

### MinIO 的优势
- ✅ 对象存储，S3 兼容
- ✅ 支持多服务器共享存储
- ✅ Web 界面管理
- ✅ 支持版本控制、生命周期管理
- ✅ 可配置高可用集群
- ✅ 独立扩展存储容量

---

## 1. 安装 MinIO

### Docker 方式（推荐）

```bash
# 创建数据目录
mkdir -p /opt/minio/data
mkdir -p /opt/minio/config

# 运行 MinIO
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin123" \
  -v /opt/minio/data:/data \
  -v /opt/minio/config:/root/.minio \
  minio/minio server /data --console-address ":9001"
```

### 访问 MinIO
- **API 地址**: http://localhost:9000
- **Web 控制台**: http://localhost:9001
- **默认账号**: minioadmin / minioadmin123

---

## 2. 创建 Bucket

1. 访问 Web 控制台：http://localhost:9001
2. 登录（使用默认账号或你设置的账号）
3. 点击 "Create Bucket"
4. 输入 Bucket 名称：`webui-files`
5. 选择 "Versioning"（可选，用于版本控制）

---

## 3. 配置 OpenWebUI 使用 MinIO

### 方法 1：环境变量（推荐）

在 `.env` 文件中添加：

```bash
# 存储提供者
STORAGE_PROVIDER=s3

# MinIO 配置（S3 兼容）
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin123
S3_BUCKET_NAME=webui-files
S3_ENDPOINT_URL=http://localhost:9000
S3_REGION_NAME=us-east-1
S3_KEY_PREFIX=openwebui/  # 可选，用于文件路径前缀
```

### 方法 2：系统环境变量

```bash
export STORAGE_PROVIDER=s3
export S3_ACCESS_KEY_ID=minioadmin
export S3_SECRET_ACCESS_KEY=minioadmin123
export S3_BUCKET_NAME=webui-files
export S3_ENDPOINT_URL=http://localhost:9000
export S3_REGION_NAME=us-east-1
```

---

## 4. 迁移现有文件到 MinIO

### 方案 A：使用 MinIO Client (mc)

```bash
# 安装 MinIO Client
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# 配置 MinIO 连接
mc alias set myminio http://localhost:9000 minioadmin minioadmin123

# 同步本地文件到 MinIO
mc mirror backend/data/uploads/ myminio/webui-files/openwebui/
```

### 方案 B：使用 Python 脚本迁移

```python
# migrate_to_minio.py
import os
import boto3
from pathlib import Path

# MinIO 配置
S3_ENDPOINT = "http://localhost:9000"
S3_ACCESS_KEY = "minioadmin"
S3_SECRET_KEY = "minioadmin123"
S3_BUCKET = "webui-files"
LOCAL_DIR = "backend/data/uploads"

# 创建 S3 客户端
s3_client = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY
)

# 上传文件
def upload_file(local_path, s3_key):
    try:
        s3_client.upload_file(local_path, S3_BUCKET, s3_key)
        print(f"✅ {local_path} -> {s3_key}")
        return True
    except Exception as e:
        print(f"❌ {local_path}: {e}")
        return False

# 遍历本地文件
local_path = Path(LOCAL_DIR)
for file_path in local_path.rglob('*'):
    if file_path.is_file():
        relative_path = file_path.relative_to(local_path)
        s3_key = f"openwebui/{relative_path}"
        upload_file(str(file_path), s3_key)

print("迁移完成！")
```

---

## 5. 验证配置

### 测试上传

```bash
# 重启 OpenWebUI 服务
# 然后尝试上传一个文件，检查是否存储到 MinIO

# 检查 MinIO 中的文件
mc ls myminio/webui-files/openwebui/ --recursive
```

---

## 6. 生产环境建议

### 安全配置

1. **修改默认密码**
   ```bash
   MINIO_ROOT_USER=your_secure_username
   MINIO_ROOT_PASSWORD=your_secure_password
   ```

2. **使用 HTTPS**
   ```bash
   # 使用 Nginx 反向代理，配置 SSL 证书
   ```

3. **访问控制**
   - 创建独立的访问密钥（Access Key / Secret Key）
   - 不要使用 Root 账号作为应用访问凭证

### 高可用配置

```bash
# MinIO 分布式模式（4 个节点）
docker run -d \
  --name minio1 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin123" \
  minio/minio server \
  http://minio{1...4}/data \
  --console-address ":9001"
```

### 备份策略

```bash
# 定期备份 MinIO 数据
mc mirror myminio/webui-files /backup/webui-files/
```

---

## 7. 性能优化

### MinIO 配置

```bash
# 增加并发上传
export MINIO_STORAGE_CLASS_STANDARD="EC:2"
```

### 网络优化

```bash
# 如果 MinIO 和 OpenWebUI 在同一服务器
S3_ENDPOINT_URL=http://127.0.0.1:9000  # 使用本地回环
```

---

## 8. 监控和维护

### 查看存储使用情况

```bash
# MinIO Web 控制台 -> Bucket -> 查看使用量
# 或使用命令行
mc du myminio/webui-files
```

### 清理旧文件

```bash
# 配置生命周期规则（在 Web 控制台）
# 或手动删除
mc rm myminio/webui-files/openwebui/old-file.jpg
```

---

## 总结

### 何时使用 MinIO？
- ✅ 文件量大（> 10GB）
- ✅ 多服务器部署
- ✅ 需要统一管理
- ✅ 需要高可用
- ✅ 需要版本控制

### 何时继续使用本地存储？
- ✅ 单服务器部署
- ✅ 文件量小（< 10GB）
- ✅ 简单场景，无需复杂管理

---

## 故障排查

### 问题：无法连接到 MinIO
```bash
# 检查 MinIO 服务状态
docker ps | grep minio

# 检查端口是否开放
netstat -tlnp | grep 9000
```

### 问题：上传失败
```bash
# 检查访问密钥
echo $S3_ACCESS_KEY_ID
echo $S3_SECRET_ACCESS_KEY

# 检查 Bucket 是否存在
mc ls myminio/
```

### 问题：文件路径错误
```bash
# 检查 S3_KEY_PREFIX 配置
# 确保路径格式正确：openwebui/knowledge/xxx/file.jpg
```



