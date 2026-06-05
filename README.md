# Dify WeCom Bridge v2

`dify-wecom-bridge` 是一个连接企业微信自建应用与 Dify Chatflow 的桥接服务。

首期目标只聚焦一条可稳定上线的主链路：

```text
企微用户发消息
    -> 企微后台（回调 URL）
    -> 中间服务（FastAPI / Flask）
    -> Dify Chatflow API
    -> 企微主动回复用户
```

## 首期范围

包含：
- 企业微信自建应用回调接入
- Dify Chatflow 对接
- Redis + SQLite 会话管理
- Docker 容器化部署

不包含：
- 群机器人主链路
- Workflow / Agent 首期实现
- 数据分析模块
- Web UI

## 目录规划

```text
dify-wecom-bridge/
├── .github/
│   └── workflows/
│       └── docker-build.yml
├── app/
│   ├── api/
│   │   ├── send.py              # Bridge API（/api/send）
│   │   └── wecom_callback.py    # 企微回调（/wecom/callback）
│   ├── channels/
│   │   └── wecom_app.py         # 企微客户端（加解密、发消息）
│   ├── dify_clients/
│   │   └── chatflow.py          # Dify Chatflow 客户端
│   ├── handlers/
│   │   └── message_handler.py   # 消息处理核心逻辑
│   ├── storage/
│   │   ├── base.py              # 存储抽象基类
│   │   ├── sqlite_client.py     # SQLite 实现
│   │   ├── mysql_client.py      # MySQL/MariaDB 实现
│   │   └── redis_client.py      # Redis 会话缓存
│   ├── config.py                # 配置（pydantic-settings）
│   └── main.py                  # FastAPI 入口
├── deploy/
│   └── dify-wecom-bridge.service  # systemd 服务文件
├── sql/
│   ├── init.sql                 # SQLite 建表脚本
│   └── init_mysql.sql           # MySQL 建表脚本
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## 核心设计约束

### 会话模型

系统使用两套 ID：
- `session_key`：本地会话定位键
- `dify_conversation_id`：Dify Chatflow 的会话 ID

`session_key` 格式：

```text
wecom_app:{corp_id}:{agent_id}:{chat_type}:{external_user_id}:{chat_id}
```

说明：
- 单聊：`chat_type=single`，`chat_id=direct`
- 群聊：`chat_type=group`，`chat_id` 使用企业微信真实 `ChatId`
- Redis 挂掉时，允许保历史但重新开新会话

### 企业微信回调策略

首期遵循企业微信官方“接收消息”协议：
- `GET /wecom/callback`：用于 URL 验证，返回解密后的 `echostr`
- `POST /wecom/callback`：接收加密 XML，验签解密后快速返回 `success`
- 实际 AI 结果不走被动回复，统一通过发送应用消息接口主动回发

### Dify 调用策略

首期仅调用：

```text
POST /chat-messages
```

建议请求体：

```json
{
  "inputs": {},
  "query": "用户消息正文",
  "response_mode": "blocking",
  "conversation_id": "命中会话时传入",
  "user": "session_key"
}
```

## 数据库

支持 SQLite 和 MySQL/MariaDB 双存储后端，通过 `DB_TYPE` 环境变量切换。

### SQLite

初始化脚本：[`sql/init.sql`](./sql/init.sql)
默认路径：`./data/dify_wecom_bridge.db`

### MySQL / MariaDB

初始化脚本：[`sql/init_mysql.sql`](./sql/init_mysql.sql)
建库建表由应用启动时自动完成，无需手动导入。

### 包含的表

| 表名 | 说明 |
|---|---|
| `conversations` | 会话记录，关联 Dify conversation_id |
| `messages` | 消息历史（用户 + AI 回复） |
| `api_logs` | Dify API 调用日志（调试用） |

## 路由说明

```text
GET  /health                             # 健康检查
GET  /wecom/callback                     # 企微 URL 验证
POST /wecom/callback                     # 接收企微消息回调
POST /api/send                           # Bridge API：主动发送消息
GET  /admin/conversations   (可选)       # 会话管理
```

### POST /api/send

供 Dify Chatflow HTTP 请求节点调用的 Bridge API，将 AI 结果主动推送给企业微信用户。

**请求体**：
```json
{
  "content": "消息内容",
  "to_user": "userid1|userid2",
  "msg_type": "markdown",
  "to_party": null,
  "to_tag": null
}
```

- `msg_type`：`text` 或 `markdown`
- `to_user` / `to_party` / `to_tag`：与企微消息推送接口一致，多个用 `|` 分隔
- 需要在请求头携带 `Authorization: Bearer <BRIDGE_API_KEY>`（若配置了 `BRIDGE_API_KEY`）

## 启动前需要准备

企业微信：
- `WECOM_CORP_ID`
- `WECOM_APP_ID`
- `WECOM_APP_SECRET`
- `WECOM_TOKEN`
- `WECOM_ENCODING_AES_KEY`

Dify：
- `DIFY_API_KEY`
- `DIFY_BASE_URL`（默认 `https://api.dify.ai/v1`）

Bridge API（可选）：
- `BRIDGE_API_KEY`：Dify HTTP 请求节点调用 Bridge 时鉴权用，留空则不鉴权

API 文档（可选）：
- `API_DOCS_ENABLED`：设为 `True` 启用 `/docs` 和 `/redoc`，生产环境建议关闭

数据库：
- `DB_TYPE`：`sqlite`（默认）或 `mysql`
- SQLite：`SQLITE_DB_PATH`（默认 `./data/dify_wecom_bridge.db`）
- MySQL：`MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE`

## 部署方式

### 方式一：Docker Compose（推荐）

```bash
git clone <your-repo-url>
cd dify-wecom-bridge
cp .env.example .env
# 编辑 .env 填入企业微信和 Dify 配置

docker compose up -d
```

服务默认监听 `http://localhost:8000`。

查看日志：
```bash
docker compose logs -f app
```

停止服务：
```bash
docker compose down
```

### 方式二：Debian 本地虚拟环境 + Docker Redis

适合开发调试，应用跑在本地 Python 虚拟环境，Redis 用 Docker 单独起。

```bash
# 1. 进入项目目录
cd dify-wecom-bridge

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，关键改动：
#   REDIS_HOST=127.0.0.1    ← 本地 venv 必须改成 127.0.0.1（默认 redis 是给 Docker 内部 DNS 用的）
#   填入企业微信和 Dify 的配置

# 5. 启动 Redis 容器（端口映射到宿主机 6379）
docker run -d --name dify-wecom-redis -p 6379:6379 redis:7-alpine redis-server --appendonly yes

# 或者复用 docker-compose.yml 里定义的 redis 服务
# docker compose up -d redis

# 6. 创建数据目录
mkdir -p data

# 7. 启动开发服务器
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

验证服务运行：
```bash
# 健康检查
curl http://127.0.0.1:8000/health

# 模拟企微回调验证（检查返回格式是否为纯文本，不带 JSON 引号）
curl "http://127.0.0.1:8000/wecom/callback?msg_signature=test&timestamp=123&nonce=abc&echostr=test"
```

### 方式三：Debian systemd 服务（推荐生产环境）

适合生产部署，使用 systemctl 管理进程，支持开机自启和故障自动重启。

```bash
# 1. 按照方式二完成项目部署到 /opt/dify-wecom-bridge，并配置好 .env

# 2. 复制服务文件
sudo cp /opt/dify-wecom-bridge/deploy/dify-wecom-bridge.service /etc/systemd/system/

# 3. 重载 systemd
sudo systemctl daemon-reload

# 4. 启动服务
sudo systemctl start dify-wecom-bridge

# 5. 设为开机自启
sudo systemctl enable dify-wecom-bridge
```

常用命令：
```bash
# 查看状态
sudo systemctl status dify-wecom-bridge

# 查看日志
sudo journalctl -u dify-wecom-bridge -f

# 重启
sudo systemctl restart dify-wecom-bridge

# 停止
sudo systemctl stop dify-wecom-bridge
```

> **注意**：`REDIS_HOST` 在不同部署方式下的取值不同：
> | 部署方式 | REDIS_HOST |
> |---|---|
> | Docker Compose 整体部署 | `redis`（容器名，Docker 内部 DNS 解析） |
> | Debian 本地 venv + Docker Redis | `127.0.0.1`（映射到宿主机端口） |

## CI/CD

项目配置了自动构建 Docker 镜像并推送到 GitHub Container Registry（GHCR）。

镜像地址：`ghcr.io/myvica/dify-wecom-bridge:latest`


