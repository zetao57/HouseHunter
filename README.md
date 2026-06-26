# 归巢 · HouseHunter

用于记录和比较看过的出租屋的 Web 应用。

## 功能

- 出租屋记录的新增、查看、编辑和删除
- 最多 8 张图片上传（浏览器端压缩）
- 租金、户型、面积、联系方式、描述和状态管理
- 浏览器定位与高德地图逆地理编码
- 搜索、状态筛选、租金排序和统计
- LocalStorage 本地持久化

## 启动

```bash
npm install
copy .env.example .env.local
npm run dev
```

在 `.env.local` 中配置高德开放平台 Web 服务 Key。未配置时仍可手动填写地址和经纬度。

## Docker with SQLite persistence

Run the app with a SQLite database stored in a local folder:

```bash
docker compose up --build
```

The app is available at http://localhost:8080 and the database is mounted at `./data/househunter.sqlite3`.

To pass the AMap key at build time:

```bash
VITE_AMAP_KEY=your_amap_key docker compose up --build
```

