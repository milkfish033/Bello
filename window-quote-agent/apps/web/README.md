# 智能报价助手 - 聊天前端

类似 ChatGPT 风格的聊天界面，对接后端 `/chat` 接口。

## 开发

1. 先启动后端（在项目根目录 `window-quote-agent` 下）：
   ```bash
   uvicorn apps.api.main:app --reload --port 8001
   ```

2. 启动前端：
   ```bash
   cd apps/web && npm install && npm run dev
   ```

3. 浏览器打开 http://localhost:5173

前端通过 Vite 代理将 `/api` 转发到 `http://127.0.0.1:8001`，无需配置 CORS。

## 构建

```bash
npm run build
```

产物在 `dist/`，可部署到任意静态托管或由 FastAPI 挂载。
