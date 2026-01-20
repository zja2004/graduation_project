# Genos Pipeline - 服务器部署与版本控制指南

本文档指导你通过 Git 将项目迁移到服务器，并利用服务器的高带宽和存储下载完整的知识库。

## 1. 版本控制 (Git) 工作流

### 1.1 初始化与提交 (本地)
如果这是你第一次使用，请在项目根目录运行：

```bash
# 初始化仓库
git init

# 添加所有文件 (除了 .gitignore 中忽略的大文件)
git add .

# 首次提交
git commit -m "Initial commit: Genos Pipeline V1.0"
```

### 1.2 推送到远程仓库 (GitHub/GitLab)
建议使用 GitHub 或私有 GitLab 托管代码。

```bash
# 关联远程仓库
git remote add origin https://github.com/zja2004/graduation_project.git

# 推送代码
git push -u origin main
```

### 1.3 日常开发流程
当你修改代码后：

```bash
git add .
git commit -m "Describe your changes here"
git push
```

---

## 2. 服务器部署

### 2.1 拉取代码
登录你的服务器，克隆代码：

```bash
# 克隆项目
git clone https://github.com/your-username/genos-pipeline.git
cd genos-pipeline
```

### 2.2 环境搭建 (推荐使用 Conda)

```bash
# 创建环境 (Python 3.10)
conda create -n genos python=3.10 -y
conda activate genos

# 安装依赖
pip install -r requirements.txt
```

---

## 3. 在服务器下载大型数据库

服务器通常具有更大存储空间（>500GB）和更好的网络。我们将利用这一点下载完整的 **gnomAD** 和 **ClinVar** 数据库，而不是使用轻量级的 API 模式。

### 3.1 使用 `screen` 后台下载 (防止断开连接中断)
下载过程可能持续数小时（数据量 >100GB），强烈建议使用 `screen`。

```bash
# 1. 创建一个名为 'download' 的后台会话
screen -S download

# 2. 运行下载脚本 (启用 --production 模式以下载所有大文件)
python tools/download_knowledge_bases.py --production

# 3. 按 Ctrl+A 然后按 D 键，将任务挂起到后台 (Detach)
# 此时你可以安全断开 SSH 连接，下载仍在继续。
```

### 3.2 查看下载进度
当你重新登录服务器时：

```bash
# 恢复会话
screen -r download
```

### 3.3 构建索引
下载完成后，必须运行索引构建脚本：

```bash
python tools/build_knowledge_index.py
```

---

## 4. 运行分析 (Server Mode)

服务器性能更强，我们使用专用的配置文件 `configs/server.yaml` (已启用 `local` 模式和更高的并发数)。

```bash
# 运行示例
python main.py \
    --config configs/server.yaml \
    --vcf examples/test.vcf \
    --output runs/server_test_01
```

## 5. 常见问题

*   **Q: 服务器下载速度太慢？**
    *   A: 尝试配置代理。`export http_proxy=http://proxy:port`。
*   **Q: 磁盘空间不足？**
    *   A: 确保 `data/` 目录所在的分区有至少 200GB 空间。如果需要移动数据目录，请修改 `configs/server.yaml` 中的路径。
