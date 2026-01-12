"""
数据库初始化脚本
在应用启动前自动创建所有数据库表并导入数据
"""
import os
import sys
import time
import subprocess
from sqlalchemy import text
from db.database import engine, Base
import os

# 从环境变量获取数据库配置（使用原始密码，不进行 URL 编码）
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Tang0312@")  # mysql 命令需要原始密码
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "aiword_db")

# 导入所有模型以确保它们被注册到 Base.metadata
from models.user import User, Session
from models.user_setting import UserSetting
from models.userlearninglogs import UserLearningLogs
from models.word import Word, UserWordProgress, WordDictionary, Book, BookWordLink
from models.user_reviewed_words import UserReviewedWords
from models.word_review_sentence import WordReviewSentence
from models.score import UserEssayResult

def wait_for_db(max_retries=30, retry_interval=2):
    """等待数据库连接可用"""
    print("等待数据库连接...")
    print(f"数据库配置: host={DB_HOST}, port={DB_PORT}, user={DB_USER}, database={DB_NAME}")
    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("数据库连接成功！")
            return True
        except Exception as e:
            if i < max_retries - 1:
                error_msg = str(e)
                # 只显示简短的错误信息，避免输出过长
                if "Can't connect" in error_msg:
                    print(f"数据库连接失败（无法连接到服务器），{retry_interval}秒后重试... ({i+1}/{max_retries})")
                elif "Access denied" in error_msg:
                    print(f"数据库连接失败（认证失败），{retry_interval}秒后重试... ({i+1}/{max_retries})")
                else:
                    print(f"数据库连接失败，{retry_interval}秒后重试... ({i+1}/{max_retries})")
                time.sleep(retry_interval)
            else:
                print(f"数据库连接失败（已重试{max_retries}次）: {e}")
                return False
    return False

def check_tables_exist():
    """检查数据库表是否已存在"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            return len(tables) > 0
    except Exception:
        return False

def check_data_exists():
    """检查数据库中是否有数据（检查关键表）"""
    try:
        with engine.connect() as conn:
            # 检查几个关键表是否有数据
            key_tables = ['words', 'books', 'users']
            for table in key_tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`"))
                    count = result.scalar()
                    if count and count > 0:
                        print(f"表 {table} 已有 {count} 条数据")
                        return True
                except Exception:
                    # 表可能不存在，继续检查其他表
                    continue
            return False
    except Exception as e:
        print(f"检查数据时出错: {e}")
        return False

def init_database_from_sql():
    """从 SQL 文件初始化数据库"""
    sql_file = os.path.join(os.path.dirname(__file__), "aiword_db.sql")
    
    if not os.path.exists(sql_file):
        print(f"警告: SQL 文件 {sql_file} 不存在，将使用模型创建空表")
        return False
    
    print(f"使用 SQL 文件初始化数据库: {sql_file}")
    
    # 使用 mysql 命令行工具执行 SQL 文件（更可靠）
    # 首先尝试不带 SSL 参数的版本（Docker 内部网络不需要 SSL）
    mysql_cmd_options = [
        [],  # 不带任何 SSL 参数
        ["--skip-ssl"],  # 尝试 --skip-ssl
    ]
    
    for ssl_option in mysql_cmd_options:
        try:
            # 构建 mysql 命令
            mysql_cmd = [
                "mysql",
                f"-h{DB_HOST}",
                f"-P{DB_PORT}",
                f"-u{DB_USER}",
                f"-p{DB_PASSWORD}",
            ] + ssl_option + [DB_NAME]
            
            with open(sql_file, 'r', encoding='utf-8') as f:
                result = subprocess.run(
                    mysql_cmd,
                    stdin=f,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5分钟超时
                )
            
            if result.returncode == 0:
                print("SQL 文件执行成功！")
                return True
            else:
                # 如果失败且不是最后一个选项，继续尝试下一个
                if ssl_option != mysql_cmd_options[-1]:
                    continue
                print(f"mysql 命令执行失败: {result.stderr}")
                print("尝试使用 SQLAlchemy 方法执行 SQL 文件...")
                # 如果所有 mysql 命令都失败，尝试使用 SQLAlchemy 执行
                return init_database_from_sql_alchemy(sql_file)
        except subprocess.TimeoutExpired:
            print("SQL 文件执行超时")
            # 如果还有更多选项，继续尝试
            if ssl_option != mysql_cmd_options[-1]:
                continue
            print("尝试使用 SQLAlchemy 方法执行 SQL 文件...")
            return init_database_from_sql_alchemy(sql_file)
        except FileNotFoundError:
            print("mysql 命令行工具未找到")
            # 直接使用 SQLAlchemy，不需要再尝试其他选项
            return init_database_from_sql_alchemy(sql_file)
        except Exception as e:
            # 如果还有更多选项，继续尝试
            if ssl_option != mysql_cmd_options[-1]:
                continue
            print(f"执行 SQL 文件时出错: {e}")
            print("尝试使用 SQLAlchemy 方法执行 SQL 文件...")
            return init_database_from_sql_alchemy(sql_file)
    
    # 如果所有选项都失败，使用 SQLAlchemy
    print("所有 mysql 命令选项都失败，使用 SQLAlchemy 方法...")
    return init_database_from_sql_alchemy(sql_file)

def init_database_from_sql_alchemy(sql_file):
    """使用 SQLAlchemy 执行 SQL 文件（备用方案）"""
    try:
        print("使用 SQLAlchemy 执行 SQL 文件...")
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割 SQL 语句（按分号和换行）
        # 移除注释和空行
        statements = []
        current_statement = ""
        
        for line in sql_content.split('\n'):
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('--') or line.startswith('/*'):
                continue
            current_statement += line + " "
            if line.endswith(';'):
                statements.append(current_statement.strip())
                current_statement = ""
        
        # 执行所有 SQL 语句
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                executed_count = 0
                error_count = 0
                for i, statement in enumerate(statements):
                    if statement:
                        try:
                            conn.execute(text(statement))
                            executed_count += 1
                            if executed_count % 100 == 0:
                                print(f"已执行 {executed_count}/{len(statements)} 条 SQL 语句...")
                        except Exception as e:
                            error_msg = str(e).lower()
                            # 忽略一些常见的错误
                            if any(keyword in error_msg for keyword in [
                                "already exists", "duplicate", "unknown table",
                                "doesn't exist", "table doesn't exist"
                            ]):
                                # 静默忽略这些错误
                                pass
                            else:
                                error_count += 1
                                if error_count <= 10:  # 只显示前10个错误
                                    print(f"警告: 执行 SQL 语句时出错 ({error_count}): {str(e)[:100]}")
                
                trans.commit()
                print(f"SQL 执行完成: 成功 {executed_count} 条，错误 {error_count} 条")
            except Exception as e:
                trans.rollback()
                raise e
        
        print("SQL 文件执行成功！")
        return True
    except Exception as e:
        print(f"使用 SQLAlchemy 执行 SQL 文件失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def init_database():
    """初始化数据库"""
    print("开始初始化数据库...")
    
    # 等待数据库就绪
    if not wait_for_db():
        print("无法连接到数据库，退出初始化")
        sys.exit(1)
    
    # 检查表是否已存在
    tables_exist = check_tables_exist()
    data_exists = check_data_exists()
    
    if tables_exist and data_exists:
        print("数据库表和数据已存在，跳过初始化")
        return True
    elif tables_exist and not data_exists:
        print("数据库表已存在但数据为空，开始导入数据...")
        # 表存在但无数据，需要导入数据
        if init_database_from_sql():
            # 验证数据是否导入成功
            if check_data_exists():
                print("数据导入成功！")
                return True
            else:
                print("警告: 数据导入可能未成功，请检查日志")
                return False
        else:
            print("数据导入失败")
            return False
    
    # 表不存在，需要完整初始化
    print("数据库表不存在，开始完整初始化...")
    
    # 尝试从 SQL 文件初始化
    if init_database_from_sql():
        # 验证表是否创建成功
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            print(f"已创建的表: {', '.join(tables)}")
        
        # 验证数据是否导入成功
        if check_data_exists():
            print("数据库初始化成功，数据已导入！")
            return True
        else:
            print("警告: 表已创建但数据可能未导入，请检查日志")
            return False
    
    # 如果 SQL 文件执行失败，使用模型创建空表
    print("SQL 文件执行失败，使用模型创建空表...")
    try:
        Base.metadata.create_all(bind=engine)
        print("数据库表创建成功！但未导入数据，请手动导入数据。")
        return True
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
