# 来源与提取边界

仅列源文件名与符号；私有路径与哈希保留在私有审查目录。

- core/phone.py::normalize：保留分隔字符、显式国际/长途前缀处理及去前缀线索。原固定手机号规则改为NumberPolicy；不保留suggest_region的原采集口径。
- core/roster.py::name_key/compare/_as_names/compare_groups/apply_classification：保留归一化比较、组集合与分类逻辑；新增重复键歧义报告；分类改为纯副本，不读取或写入默认名册。
- core/seats.py::devices_by_keys：保留显式设备选择顺序，未知/重复标识改为明确错误，不加载配置文件。
- core/codes.py::build_plan/verify_no_chaining：保留按设备/变体规划与目标一致性机制，全部模板/前缀外置为调用方参数；只生成文字预览。没有原设置/取消指令与区号。

CLI、格式合同、合成例子、边界测试为本次新写。原HTML、data目录、Excel与真实名单未复制、未执行、未作为测试输入。此记录不授予代码许可，不代表原完整程序已经迁移。
