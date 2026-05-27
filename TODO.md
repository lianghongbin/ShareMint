# 团长分佣管理系统（Django 版）开发 TODO 清单

## 📅 Step 1: 项目基础骨架与环境初始化

- [x] 1.1 环境初始化： 创建 Python 虚拟环境，安装 django, djangorestframework, django-cors-headers。
- [x] 1.2 项目创建： 使用 django-admin startproject core . 创建工程，并划分 authentication（认证）, management（业务管理）, commissions（分佣引擎）三个 App。
- [x] 1.3 数据库配置： 配置本地数据库连接（SQLite 或 PostgreSQL），并在 settings.py 中注册各 App、时区设定为 Asia/Shanghai。

## 🔒 Step 2: 用户、扩展档案与严格权限体系 (RBAC)

- [x] 2.1 自定义用户模型 (AbstractUser)：
  - 继承 Django 自带用户类，添加 role 字段（枚举：Admin/Headman/Member）。添加 is_first_login 字段（布尔值，默认 True）。添加 referrer 字段（自引用外键，指向团长用户，普通成员必填）。
- [x] 2.2 用户档案表 (User Profile)：创建 Profile 模型，字段包含：姓名、手机号、微信号、邮箱。在 Django Admin 或 API 序列化器中限制：普通成员的"姓名"字段设为只读（Read-Only）。
- [x] 2.3 资产与投资数据表 (Asset / Investment)：绑定普通成员，字段包含：投资时间、投资金额（Decimal，单位 USDT）、持有数量、持有币种（默认 GDT）。
- [x] 2.4 首次登录强制修改密码拦截器 (Middleware)：编写 Django 中间件，检测如果用户 is_first_login == True 且访问的不是修改密码接口，一律强制重定向/拦截并提示跳转至密码修改页面。

## 💰 Step 3: 单一水源价格控制与阶梯分佣引擎

- [x] 3.1 系统全局配置表 (SystemConfig)：设计键值对表，用来存放全局唯一的 GDT_CURRENT_PRICE（GDT 当前价格），作为全局唯一引用源。设计动态分成比例梯度的 JSON 配置项。
- [x] 3.2 资产价值动态计算：在模型或序列化器中编写 Property 属性：当前市值 = 持有数量 * 引用自 SystemConfig 的当前价格。
- [x] 3.3 团长阶梯提成计算核心算法 (基于手写图纸规则)：编写计算服务，自动汇总某个团长线下所有普通成员的"总投资金额"。根据总金额自动归类梯度并计算提成：
  - 团队总业绩 1w - 10w USDT → 5%
  - 团队总业绩 10w - 20w USDT → 8%
  - 团队总业绩 20w - 50w USDT → 10%
  - 团队总业绩 50w - 100w USDT → 12%
  - 团队总业绩 100w - 200w USDT → 15%
  - 团长额外享有 5% 的大团长基础底薪/奖励（根据配置决定发放 USDT 或 GDT）。

## 🖥️ Step 4: 角色专属功能集与视图层开发

### 👑 4.1 系统管理员 (Admin) 视图

- [x] 4.1.1 团长开户： 支持创建和初始化团长账号。
- [x] 4.1.2 状态锁控制： 支持一键"锁定/解锁"团长。当状态为锁定（Locked）时，拦截该团长添加新成员和修改数据的 POST/PUT 请求，仅允许 GET 查看。
- [x] 4.1.3 全局调价： 提供一键修改全局 GDT 价格的表单。

### 👥 4.2 团长 (Headman) 视图

- [x] 4.2.1 个人资料维护： 修改自己的手机号、微信号、邮箱、姓名。
- [x] 4.2.2 线下团队录入： 校验若未被管理员锁定，可手动添加新成员，并直接录入其初始资料、投资金额、代币数量。
- [x] 4.2.3 团长数据看板： 实时聚合显示：当前总人数、总投资金额、总代币数、团队资产总价值。

### 👤 4.3 普通成员 (Member) 视图

- [x] 4.3.1 自助资料更新： 自主修改手机、微信、邮箱。姓名置灰防篡改。
- [x] 4.3.2 归属查看： 个人主页清晰展示自己隶属的团长姓名及联系方式。
- [x] 4.3.3 投资清册： 个人看板直观展现投资时间、USDT 金额、持币数量和实时动态市值。

## 🛠️ Step 5: 核心底层运维工具（备份、恢复与第三方登录）

- [x] 5.1 自动化数据备份与恢复 (Backup & Restore)：利用 Django 的 dumpdata 和 loaddata 核心底层逻辑，封装成后台一键执行的数据库全量备份（导出标准 JSON/SQL）与一键还原功能。
- [x] 5.2 第三方集成：集成 django-allauth 或预留标准的 OAuth3/飞机群（Telegram WebApp）登录认证解耦接口。

## 🎨 UI 规范

- [x] 全终端自适应布局（Mobile-First 响应式）
- [x] Crypto 科技蓝主题风格与 SVG 图标体系
