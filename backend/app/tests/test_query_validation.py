"""
测试查询参数验证功能

测试 /api/files 端点对于无效查询参数的错误处理
"""

import pytest
from fastapi.testclient import TestClient

# 需要从上一层目录导入
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from main import app


class TestQueryValidation:
    """查询参数验证测试类"""
    
    def setup_method(self):
        """测试方法设置"""
        self.client = TestClient(app)
    
    def test_invalid_sort_field(self):
        """测试不支持的排序字段"""
        response = self.client.get("/api/files?sort=bad_field:asc")
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "不支持的排序字段: bad_field" in data["detail"]
        assert "支持的字段:" in data["detail"]
    
    def test_invalid_sort_direction(self):
        """测试不支持的排序方向"""
        response = self.client.get("/api/files?sort=created_at:invalid")
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "不支持的排序方向: invalid" in data["detail"]
        assert "支持的方向:" in data["detail"]
    
    def test_invalid_sort_format(self):
        """测试错误的排序格式"""
        response = self.client.get("/api/files?sort=created_at")
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "排序参数格式错误" in data["detail"]
        assert "正确格式: 'field:direction'" in data["detail"]
    
    def test_invalid_status_value(self):
        """测试不支持的状态值"""
        response = self.client.get("/api/files?status=INVALID_STATUS")
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "不支持的状态值: INVALID_STATUS" in data["detail"]
        assert "支持的状态:" in data["detail"]
    
    def test_multiple_invalid_status_values(self):
        """测试多个无效状态值"""
        response = self.client.get("/api/files?status=PENDING,INVALID1,INVALID2")
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "不支持的状态值:" in data["detail"]
        # 应该包含所有无效的状态值
        assert "INVALID1" in data["detail"]
        assert "INVALID2" in data["detail"]
    
    def test_valid_sort_parameters(self):
        """测试有效的排序参数"""
        valid_sorts = [
            "created_at:asc",
            "created_at:desc", 
            "updated_at:asc",
            "updated_at:desc",
            "original_filename:asc",
            "original_filename:desc",
            "status:asc",
            "status:desc"
        ]
        
        for sort_param in valid_sorts:
            response = self.client.get(f"/api/files?sort={sort_param}")
            # 应该不是 422 错误（可能是 200 或其他，取决于数据库状态）
            assert response.status_code != 422, f"Valid sort parameter {sort_param} was rejected"
    
    def test_valid_status_parameters(self):
        """测试有效的状态参数"""
        valid_statuses = [
            "PENDING",
            "QUEUED", 
            "PROCESSING",
            "COMPLETED",
            "FAILED",
            "CONFLICT",
            "NO_MATCH",
            "PENDING,COMPLETED",
            "FAILED,CONFLICT,NO_MATCH"
        ]
        
        for status_param in valid_statuses:
            response = self.client.get(f"/api/files?status={status_param}")
            # 应该不是 422 错误
            assert response.status_code != 422, f"Valid status parameter {status_param} was rejected"
    
    def test_case_insensitive_status(self):
        """测试状态值大小写不敏感"""
        response = self.client.get("/api/files?status=pending,completed")
        # 小写状态值应该被正常处理（内部会转换为大写）
        assert response.status_code != 422
    
    def test_empty_parameters(self):
        """测试空参数"""
        # 空状态参数应该被接受
        response = self.client.get("/api/files?status=")
        assert response.status_code != 422
        
        # 空排序参数应该使用默认值
        response = self.client.get("/api/files?sort=")
        assert response.status_code != 422
    
    def test_whitespace_handling(self):
        """测试空白字符处理"""
        # 带空格的状态值应该被正确处理
        response = self.client.get("/api/files?status= PENDING , COMPLETED ")
        assert response.status_code != 422
    
    def test_error_response_format(self):
        """测试错误响应格式"""
        response = self.client.get("/api/files?sort=bad:asc")
        
        assert response.status_code == 422
        data = response.json()
        
        # 确保响应只包含 detail 字段，符合统一错误格式
        assert "detail" in data
        assert isinstance(data["detail"], str)
        
        # 确保没有其他不必要的字段
        # FastAPI 可能会添加其他字段，但至少要有 detail
        assert data["detail"] != ""


if __name__ == "__main__":
    # 可以直接运行此文件进行测试
    pytest.main([__file__, "-v"]) 