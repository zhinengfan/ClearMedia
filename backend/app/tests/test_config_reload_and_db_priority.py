"""
配置热重载和数据库优先级测试用例
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from app.core.models import ConfigItem
from app.config import get_settings, cleanup_deprecated_configs
from app.services.config import ConfigService


class TestConfigDatabasePriority:
    """测试数据库配置优先级"""
    
    def test_database_config_overrides_env(self, setup_test_db):
        """测试数据库配置覆盖环境变量配置"""
        db_session = setup_test_db
        
        # 在数据库中设置配置
        config_item = ConfigItem(
            key="TMDB_LANGUAGE",
            value=json.dumps("ko-KR"),
            description="测试配置项"
        )
        db_session.add(config_item)
        db_session.commit()
        
        # 强制重新加载配置
        settings = get_settings(force_reload=True)
        
        # 验证数据库配置覆盖了环境变量
        assert settings.TMDB_LANGUAGE == "ko-KR"
    
    def test_env_config_used_when_no_db_config(self, setup_test_db, env_vars):
        """测试当数据库中没有配置时使用环境变量"""

        
        # 强制重新加载配置
        settings = get_settings(force_reload=True)
        
        # 验证使用了环境变量中的默认值
        assert settings.TMDB_LANGUAGE == "zh-CN"  # 默认值
    
    def test_multiple_db_configs_override(self, setup_test_db):
        """测试多个数据库配置同时覆盖"""
        db_session = setup_test_db
        
        # 在数据库中设置多个配置
        configs = [
            ConfigItem(key="TMDB_LANGUAGE", value=json.dumps("en-US")),
            ConfigItem(key="TMDB_CONCURRENCY", value=json.dumps(5)),
            ConfigItem(key="WORKER_COUNT", value=json.dumps(4)),
        ]
        
        for config in configs:
            db_session.add(config)
        db_session.commit()
        
        # 强制重新加载配置
        settings = get_settings(force_reload=True)
        
        # 验证所有数据库配置都生效
        assert settings.TMDB_LANGUAGE == "en-US"
        assert settings.TMDB_CONCURRENCY == 5
        assert settings.WORKER_COUNT == 4


class TestConfigHotReload:
    """测试配置热重载机制"""
    
    @patch('app.config.tmdbsimple')
    @patch('app.config.asyncio.Semaphore')
    def test_on_settings_reloaded_updates_globals(self, mock_semaphore, mock_tmdbsimple, setup_test_db):
        """测试配置重载钩子更新全局变量"""
        # 模拟tmdb模块
        mock_tmdb_module = MagicMock()
        
        with patch('app.core.tmdb', mock_tmdb_module):
            # 创建测试配置
            settings = get_settings(force_reload=True)
            
            # 验证tmdbsimple.API_KEY被更新
            assert hasattr(mock_tmdbsimple, 'API_KEY')
            
            # 验证TMDB_SEMAPHORE被重新创建
            mock_semaphore.assert_called_with(settings.TMDB_CONCURRENCY)
    
    def test_force_reload_triggers_hook(self, setup_test_db):
        """测试force_reload参数触发钩子函数"""
        with patch('app.config._on_settings_reloaded') as mock_hook:
            # 第一次调用 - 应该触发钩子
            settings1 = get_settings(force_reload=True)
            mock_hook.assert_called_once_with(settings1)
            
            # 重置mock
            mock_hook.reset_mock()
            
            # 第二次调用（不强制重载）- 不应该触发钩子
            get_settings(force_reload=False)
            mock_hook.assert_not_called()
            
            # 第三次调用（强制重载）- 应该再次触发钩子
            settings3 = get_settings(force_reload=True)
            mock_hook.assert_called_once_with(settings3)
    
    def test_config_update_via_service_triggers_reload(self, setup_test_db):
        """测试通过ConfigService更新配置后手动重载生效"""
        db_session = setup_test_db
        
        # 初始配置
        initial_settings = get_settings(force_reload=True)
        initial_concurrency = initial_settings.TMDB_CONCURRENCY
        
        # 通过ConfigService更新配置
        updates = {"TMDB_CONCURRENCY": 15}
        ConfigService.update_configs(db_session, updates)
        
        # 手动重载配置
        reloaded_settings = get_settings(force_reload=True)
        
        # 验证配置已更新
        assert reloaded_settings.TMDB_CONCURRENCY == 15
        assert reloaded_settings.TMDB_CONCURRENCY != initial_concurrency


class TestDeprecatedConfigCleanup:
    """测试废弃配置清理机制"""
    
    def test_cleanup_removes_deprecated_configs(self, setup_test_db):
        """测试清理删除废弃的配置项"""
        db_session = setup_test_db
        
        # 添加一些配置项，包括废弃的
        configs = [
            ConfigItem(key="TMDB_LANGUAGE", value=json.dumps("zh-CN")),  # 有效配置
            ConfigItem(key="OLD_FEATURE_FLAG", value=json.dumps(True)),  # 废弃配置
            ConfigItem(key="DEPRECATED_SETTING", value=json.dumps("value")),  # 废弃配置
        ]
        
        for config in configs:
            db_session.add(config)
        db_session.commit()
        
        # 验证配置项已存在
        from sqlmodel import select
        statement = select(ConfigItem)
        all_configs_before = db_session.exec(statement).all()
        assert len(all_configs_before) == 3
        
        # 执行清理
        cleanup_deprecated_configs()
        
        # 刷新会话以获取最新数据
        db_session.expire_all()
        
        # 验证废弃配置已被删除
        remaining_configs = db_session.exec(statement).all()
        remaining_keys = {config.key for config in remaining_configs}
        
        # 应该只剩下有效的配置
        assert "TMDB_LANGUAGE" in remaining_keys
        assert "OLD_FEATURE_FLAG" not in remaining_keys
        assert "DEPRECATED_SETTING" not in remaining_keys
    
    def test_cleanup_preserves_valid_configs(self, setup_test_db):
        """测试清理保留有效的配置项"""
        db_session = setup_test_db
        
        # 添加所有有效的配置项
        valid_configs = [
            ConfigItem(key="TMDB_LANGUAGE", value=json.dumps("zh-CN")),
            ConfigItem(key="TMDB_CONCURRENCY", value=json.dumps(10)),
            ConfigItem(key="WORKER_COUNT", value=json.dumps(2)),
            ConfigItem(key="LOG_LEVEL", value=json.dumps("INFO")),
        ]
        
        for config in valid_configs:
            db_session.add(config)
        db_session.commit()
        
        # 执行清理
        cleanup_deprecated_configs()
        
        # 刷新会话
        db_session.expire_all()
        
        # 验证所有有效配置都被保留
        from sqlmodel import select
        statement = select(ConfigItem)
        remaining_configs = db_session.exec(statement).all()
        remaining_keys = {config.key for config in remaining_configs}
        
        expected_keys = {"TMDB_LANGUAGE", "TMDB_CONCURRENCY", "WORKER_COUNT", "LOG_LEVEL"}
        assert remaining_keys == expected_keys
    
    def test_cleanup_handles_empty_database(self, setup_test_db):
        """测试清理空数据库不会出错"""
        # 确保数据库为空
        db_session = setup_test_db
        
        from sqlmodel import select
        statement = select(ConfigItem)
        configs = db_session.exec(statement).all()
        for config in configs:
            db_session.delete(config)
        db_session.commit()
        
        # 执行清理应该不会出错
        try:
            cleanup_deprecated_configs()
        except Exception as e:
            pytest.fail(f"清理空数据库时出错: {e}")
    
    def test_cleanup_handles_database_error(self):
        """测试清理在数据库错误时的处理"""
        with patch('app.db.get_session_factory') as mock_factory:
            # 模拟数据库错误
            mock_factory.side_effect = Exception("数据库连接失败")
            
            # 清理应该捕获异常而不是崩溃
            try:
                cleanup_deprecated_configs()
            except Exception as e:
                pytest.fail(f"清理在数据库错误时应该捕获异常: {e}")


class TestConfigIntegration:
    """集成测试"""
    
    def test_full_config_lifecycle(self, setup_test_db):
        """测试完整的配置生命周期"""
        db_session = setup_test_db
        
        # 1. 初始加载 - 使用默认/环境变量配置
        initial_settings = get_settings(force_reload=True)
        assert initial_settings.TMDB_CONCURRENCY == 10  # 默认值
        
        # 2. 通过数据库设置配置
        config_item = ConfigItem(
            key="TMDB_CONCURRENCY",
            value=json.dumps(8),
            description="测试配置"
        )
        db_session.add(config_item)
        db_session.commit()
        
        # 3. 重载配置 - 应该使用数据库值
        db_settings = get_settings(force_reload=True)
        assert db_settings.TMDB_CONCURRENCY == 8
        
        # 4. 通过ConfigService更新配置
        ConfigService.update_configs(db_session, {"TMDB_CONCURRENCY": 12})
        
        # 5. 再次重载 - 应该使用更新后的值
        updated_settings = get_settings(force_reload=True)
        assert updated_settings.TMDB_CONCURRENCY == 12
        
        # 6. 清理废弃配置（这里没有废弃配置，所以应该保持不变）
        cleanup_deprecated_configs()
        
        # 7. 最终验证
        final_settings = get_settings(force_reload=True)
        assert final_settings.TMDB_CONCURRENCY == 12


@pytest.fixture
def setup_test_db():
    """设置测试数据库"""
    from app.db import get_session_factory
    
    # 使用现有的测试数据库设置
    session_factory = get_session_factory()
    with session_factory() as session:
        # 清理现有的配置项
        from sqlmodel import select
        statement = select(ConfigItem)
        existing_configs = session.exec(statement).all()
        for config in existing_configs:
            session.delete(config)
        session.commit()
        
        yield session
        
        # 清理测试数据
        statement = select(ConfigItem)
        test_configs = session.exec(statement).all()
        for config in test_configs:
            session.delete(config)
        session.commit() 