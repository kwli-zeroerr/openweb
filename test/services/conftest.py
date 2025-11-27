"""
pytest配置文件
提供测试所需的fixtures和配置
"""
import sys
import os

# 添加backend目录到路径
sys.path.insert(0, '/home/zeroerr-ai72/openwebui-zeroerr/backend')

# 设置测试环境变量
os.environ['ENV'] = 'test'
