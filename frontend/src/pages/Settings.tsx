export function Settings() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-secondary-900 mb-4">系统设置</h1>
      <p className="text-secondary-600">配置系统参数</p>
      <div className="mt-6 space-y-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-secondary-900 mb-3">
            存储设置
          </h3>
          <p className="text-secondary-500 mb-4">配置文件存储路径和限制</p>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-secondary-700">
                存储路径
              </label>
              <input
                type="text"
                className="mt-1 block w-full px-3 py-2 border border-secondary-300 rounded-md shadow-sm placeholder-secondary-400"
                placeholder="/path/to/storage"
                disabled
              />
            </div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-secondary-900 mb-3">
            系统配置
          </h3>
          <p className="text-secondary-500 mb-4">系统运行相关参数配置</p>
          <div className="space-y-3">
            <div className="flex items-center">
              <input type="checkbox" className="mr-2" disabled />
              <label className="text-sm text-secondary-700">启用缓存</label>
            </div>
            <div className="flex items-center">
              <input type="checkbox" className="mr-2" disabled />
              <label className="text-sm text-secondary-700">自动备份</label>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Settings;
