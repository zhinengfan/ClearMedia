"""
ConfigService的单元测试

测试配置服务的所有核心功能，包括：
1. 黑名单过滤机制
2. 空数据库处理
3. Pydantic验证和事务回滚
4. 成功更新配置项
"""

import json
import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from pydantic import ValidationError

from app.services.config import ConfigService, get_config_blacklist
from app.core.models import ConfigItem


@pytest.fixture
def in_memory_db():
    """
    创建内存SQLite数据库的pytest fixture。
    
    每个测试使用独立的内存数据库，测试完成后自动清理。
    """
    # 创建内存数据库引擎
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,  # 测试时不输出SQL语句
        connect_args={"check_same_thread": False}
    )
    
    # 创建所有表
    SQLModel.metadata.create_all(engine)
    
    # 创建数据库会话
    with Session(engine) as session:
        yield session


class TestConfigServiceReadAll:
    """测试ConfigService.read_all_from_db方法"""
    
    def test_read_empty_database(self, in_memory_db: Session):
        """测试从空数据库读取配置应返回空字典"""
        result = ConfigService.read_all_from_db(in_memory_db)
        assert result == {}
        
    def test_read_existing_configs(self, in_memory_db: Session):
        """测试从有数据的数据库读取配置"""
        # 预先插入一些配置项
        test_configs = [
            ConfigItem(key="LOG_LEVEL", value=json.dumps("DEBUG"), description="测试日志级别"),
            ConfigItem(key="WORKER_COUNT", value=json.dumps(3), description="测试工作者数量"),
            ConfigItem(key="OPENAI_MODEL", value=json.dumps("gpt-4"), description="测试模型配置"),
        ]
        
        for config in test_configs:
            in_memory_db.add(config)
        in_memory_db.commit()
        
        # 读取配置
        result = ConfigService.read_all_from_db(in_memory_db)
        
        # 验证结果
        assert len(result) == 3
        assert result["LOG_LEVEL"] == "DEBUG"
        assert result["WORKER_COUNT"] == 3
        assert result["OPENAI_MODEL"] == "gpt-4"
        
    def test_read_configs_with_invalid_json(self, in_memory_db: Session):
        """测试读取包含无效JSON的配置项时应忽略无效项"""
        # 插入有效和无效的配置项
        valid_config = ConfigItem(key="LOG_LEVEL", value=json.dumps("DEBUG"))
        invalid_config = ConfigItem(key="INVALID_JSON", value="{ invalid json }")
        
        in_memory_db.add(valid_config)
        in_memory_db.add(invalid_config)
        in_memory_db.commit()
        
        # 读取配置
        result = ConfigService.read_all_from_db(in_memory_db)
        
        # 应该只包含有效的配置项
        assert len(result) == 1
        assert result["LOG_LEVEL"] == "DEBUG"
        assert "INVALID_JSON" not in result


class TestConfigServiceBlacklist:
    """测试ConfigService的黑名单过滤机制"""
    
    def test_blacklist_contains_expected_keys(self):
        """测试黑名单包含预期的配置项"""
        blacklist = get_config_blacklist()
        expected_keys = {"DATABASE_URL", "ENABLE_TMDB", "ENABLE_LLM"}
        assert expected_keys.issubset(blacklist)
        
    def test_blacklist_excludes_configurable_keys(self):
        """测试黑名单正确排除可配置的配置项"""
        blacklist = get_config_blacklist()
        configurable_keys = {"OPENAI_API_BASE", "OPENAI_MODEL", "TMDB_LANGUAGE", "LOG_LEVEL", "WORKER_COUNT"}
        assert configurable_keys.isdisjoint(blacklist)
        
    def test_update_excludes_blacklist_keys(self, in_memory_db: Session):
        """测试黑名单内的配置项不会被更新"""
        updates = {
            "LOG_LEVEL": "WARNING",          # 不在黑名单内，应该被更新
            "WORKER_COUNT": 5,               # 不在黑名单内，应该被更新
            "DATABASE_URL": "sqlite:///hack.db",  # 在黑名单内，应该被忽略
            "ENABLE_TMDB": False,            # 在黑名单内，应该被忽略
        }
        
        # 执行更新
        ConfigService.update_configs(in_memory_db, updates)
        
        # 检查数据库中的配置项
        statement = select(ConfigItem)
        config_items = in_memory_db.exec(statement).all()
        
        # 应该只有不在黑名单内的配置项被保存
        saved_keys = {item.key for item in config_items}
        assert saved_keys == {"LOG_LEVEL", "WORKER_COUNT"}
        
        # 验证保存的值
        config_dict = {item.key: json.loads(item.value) for item in config_items}
        assert config_dict["LOG_LEVEL"] == "WARNING"
        assert config_dict["WORKER_COUNT"] == 5


class TestConfigServiceValidation:
    """测试ConfigService的Pydantic验证机制"""
    
    def test_update_with_invalid_log_level(self, in_memory_db: Session):
        """测试使用无效的LOG_LEVEL值应该抛出ValidationError"""
        updates = {"LOG_LEVEL": "INVALID_LEVEL"}
        
        with pytest.raises(ValidationError):
            ConfigService.update_configs(in_memory_db, updates)
            
        # 验证数据库中没有任何配置项被保存（事务回滚）
        statement = select(ConfigItem)
        config_items = in_memory_db.exec(statement).all()
        assert len(config_items) == 0
        
    def test_update_with_invalid_worker_count(self, in_memory_db: Session):
        """测试使用无效的WORKER_COUNT值应该抛出ValidationError"""
        updates = {"WORKER_COUNT": 0}  # 应该 >= 1
        
        with pytest.raises(ValidationError):
            ConfigService.update_configs(in_memory_db, updates)
            
        # 验证数据库中没有任何配置项被保存（事务回滚）
        statement = select(ConfigItem)
        config_items = in_memory_db.exec(statement).all()
        assert len(config_items) == 0
        
    def test_update_with_invalid_video_extensions(self, in_memory_db: Session):
        """测试使用无效的VIDEO_EXTENSIONS格式应该抛出ValidationError"""
        updates = {"VIDEO_EXTENSIONS": "mp4,avi"}  # 缺少点号前缀
        
        with pytest.raises(ValidationError):
            ConfigService.update_configs(in_memory_db, updates)
            
        # 验证数据库中没有任何配置项被保存（事务回滚）
        statement = select(ConfigItem)
        config_items = in_memory_db.exec(statement).all()
        assert len(config_items) == 0
        
    def test_partial_validation_failure_rollback(self, in_memory_db: Session):
        """测试部分更新验证失败时整个事务应该回滚"""
        # 混合有效和无效的配置更新
        updates = {
            "LOG_LEVEL": "ERROR",           # 有效
            "WORKER_COUNT": -1,             # 无效，应该 >= 1
            "OPENAI_MODEL": "gpt-4",        # 有效
        }
        
        with pytest.raises(ValidationError):
            ConfigService.update_configs(in_memory_db, updates)
            
        # 验证即使有有效的配置项，整个事务都被回滚了
        statement = select(ConfigItem)
        config_items = in_memory_db.exec(statement).all()
        assert len(config_items) == 0


class TestConfigServiceSuccessfulUpdates:
    """测试ConfigService的成功更新场景"""
    
    def test_create_new_configs(self, in_memory_db: Session):
        """测试创建新的配置项"""
        updates = {
            "LOG_LEVEL": "WARNING",
            "WORKER_COUNT": 4,
            "OPENAI_MODEL": "gpt-4",
        }
        
        # 执行更新
        ConfigService.update_configs(in_memory_db, updates)
        
        # 验证配置项被正确保存
        result = ConfigService.read_all_from_db(in_memory_db)
        assert result["LOG_LEVEL"] == "WARNING"
        assert result["WORKER_COUNT"] == 4
        assert result["OPENAI_MODEL"] == "gpt-4"
        
    def test_update_existing_configs(self, in_memory_db: Session):
        """测试更新现有的配置项"""
        # 先创建一些初始配置
        initial_config = ConfigItem(
            key="LOG_LEVEL", 
            value=json.dumps("DEBUG"), 
            description="初始日志级别"
        )
        in_memory_db.add(initial_config)
        in_memory_db.commit()
        
        # 更新配置
        updates = {"LOG_LEVEL": "ERROR"}
        ConfigService.update_configs(in_memory_db, updates)
        
        # 验证配置被更新
        result = ConfigService.read_all_from_db(in_memory_db)
        assert result["LOG_LEVEL"] == "ERROR"
        
        # 验证数据库中只有一个LOG_LEVEL配置项（更新而非新增）
        statement = select(ConfigItem).where(ConfigItem.key == "LOG_LEVEL")
        config_items = in_memory_db.exec(statement).all()
        assert len(config_items) == 1
        
    def test_mixed_create_and_update(self, in_memory_db: Session):
        """测试同时创建新配置和更新现有配置"""
        # 先创建一个初始配置
        initial_config = ConfigItem(
            key="LOG_LEVEL", 
            value=json.dumps("DEBUG")
        )
        in_memory_db.add(initial_config)
        in_memory_db.commit()
        
        # 混合更新：更新现有配置，创建新配置
        updates = {
            "LOG_LEVEL": "WARNING",    # 更新现有
            "WORKER_COUNT": 3,         # 创建新的
            "OPENAI_MODEL": "gpt-4",   # 创建新的
        }
        
        ConfigService.update_configs(in_memory_db, updates)
        
        # 验证所有配置都正确
        result = ConfigService.read_all_from_db(in_memory_db)
        assert len(result) == 3
        assert result["LOG_LEVEL"] == "WARNING"
        assert result["WORKER_COUNT"] == 3
        assert result["OPENAI_MODEL"] == "gpt-4"
        
    def test_empty_updates(self, in_memory_db: Session):
        """测试空更新不应该影响数据库"""
        # 先添加一些配置
        initial_config = ConfigItem(key="LOG_LEVEL", value=json.dumps("DEBUG"))
        in_memory_db.add(initial_config)
        in_memory_db.commit()
        
        # 执行空更新
        ConfigService.update_configs(in_memory_db, {})
        
        # 验证原有配置保持不变
        result = ConfigService.read_all_from_db(in_memory_db)
        assert result["LOG_LEVEL"] == "DEBUG"
        
    def test_updates_with_only_blacklist_keys(self, in_memory_db: Session):
        """测试只包含黑名单键的更新应该被完全忽略"""
        updates = {
            "DATABASE_URL": "sqlite:///hack.db",
            "ENABLE_TMDB": False,
            "ENABLE_LLM": True,
        }
        
        # 执行更新
        ConfigService.update_configs(in_memory_db, updates)
        
        # 验证数据库中没有任何配置项
        statement = select(ConfigItem)
        config_items = in_memory_db.exec(statement).all()
        assert len(config_items) == 0


class TestConfigServiceIntegration:
    """配置服务集成测试"""
    
    def test_read_write_cycle(self, in_memory_db: Session):
        """测试完整的读写周期"""
        # 1. 初始状态：空数据库
        result = ConfigService.read_all_from_db(in_memory_db)
        assert result == {}
        
        # 2. 写入一些配置
        updates = {
            "LOG_LEVEL": "INFO",
            "WORKER_COUNT": 2,
            "OPENAI_MODEL": "gpt-4",
            "TMDB_LANGUAGE": "en-US",
        }
        ConfigService.update_configs(in_memory_db, updates)
        
        # 3. 读取并验证
        result = ConfigService.read_all_from_db(in_memory_db)
        assert len(result) == 4
        assert result["LOG_LEVEL"] == "INFO"
        assert result["WORKER_COUNT"] == 2
        assert result["OPENAI_MODEL"] == "gpt-4"
        assert result["TMDB_LANGUAGE"] == "en-US"
        
        # 4. 部分更新
        partial_updates = {
            "LOG_LEVEL": "ERROR",
            "WORKER_COUNT": 5,
        }
        ConfigService.update_configs(in_memory_db, partial_updates)
        
        # 5. 验证部分更新结果
        result = ConfigService.read_all_from_db(in_memory_db)
        assert len(result) == 4  # 总数不变
        assert result["LOG_LEVEL"] == "ERROR"      # 已更新
        assert result["WORKER_COUNT"] == 5         # 已更新
        assert result["OPENAI_MODEL"] == "gpt-4"   # 保持不变
        assert result["TMDB_LANGUAGE"] == "en-US"  # 保持不变 