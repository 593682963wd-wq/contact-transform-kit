# 显式联系信息转换核心

保留原工具的号码格式归一化、名单差异、分组候选、设备选择与模板预览算法。所有名单、编号格式、设备和模板都由调用方明确提供；没有内置公司名单、设备配置、运营商指令或归属地规则。

Python 3.11+，仅标准库：

```sh
python3 -B cli.py example.json
python3 -B cli.py example.json --output result.json
python3 -B -m unittest discover -s tests -v
```

输入最大1MiB，输出文件独占创建，已有文件不会被覆盖；输入错误退出2，不打印调用栈。默认只输出到终端，无后台服务、拨号、发送、GUI、目录扫描或源名册写入。

## 可执行能力

| action / 库入口 | 功能 |
|---|---|
| normalize / phone.normalize | 根据显式national_lengths/national_prefixes、国码、国际前缀和长途前缀处理常见空格/横线/括号格式。无效行保留失败标记；禁止字母、分机、多个号码等被盲目拼接成有效值。 |
| compare / roster.compare | 匹配、左右独有项、重复归一化键歧义。可选去括号标签，保留原显示值，不用最后一条覆盖同名人员。 |
| compare_groups / roster.compare_groups | 每组人数、名单差异、一人多组候选及未入任何组者；同名歧义不自动归属。 |
| classify / roster.classify | 生成分类副本，保留其他字段，不修改输入对象和源文件；没有正式组织归属判断。 |
| plan / templates.build_plan | 按显式设备/模板生成目标和取消预览；变体未确认时同时给出可选变体，未配置类型/未知设备/重复key明确失败。 |
| verify_targets / templates.verify_targets | 检查预览里声明目标与长数字串是否符合调用方给定目标及允许前缀；不理解任意运营商命令语义，也不证明已生效。 |

这是独立通用子集，不是完整原通信工具。`sent`始终false，`template_semantics_verified`始终false。程序没有外发能力，模板只是普通文字。

## 输入举例

格式规则没有默认国家、地区或号码长度，必须配置。示例使用虚构的202-555-01xx号码段与DEMO文字模板，没有可执行的运营商命令。

```json
{"action":"normalize","policy":{"national_lengths":[10],"country_code":"1","international_prefix":"00","trunk_prefix":"0"},"numbers":["+1 (202) 555-0101","0 202-555-0101","not-a-number"]}
```

返回`national`/`valid`/`reason`及`country_removed`/`trunk_removed`。格式有效不证明号码存在、可达或归属；不根据前导零推断地理归属。裸国码默认不删除；明确设置`allow_bare_country_code:true`时，仅在完整输入不符合国内格式时尝试去国码。数字型JSON输入会失败，以免掩盖前导零或数值精度丢失。

```json
{"action":"compare","left":["Synthetic A (team)","Synthetic B"],"right":["Synthetic A","Synthetic C"],"strip_parentheses":true}
```

`left`/`right`可以是文本数组或逗号/分号/换行分隔文本；名字内部空格保留为一个空格。含分隔符的名字请使用数组。Unicode统一为NFC，大小写敏感，不做拼音或模糊身份匹配。

```json
{"action":"classify","people":[{"name":"Synthetic A"},{"name":"Synthetic B"}],"groups":{"demo-one":["Synthetic A"],"demo-two":["Synthetic A"]}}
```

可选`name_field`、`group_field`。分类副本中group_field会被本次结果替换，未匹配或歧义者为空数组；`comparison`保留候选组与歧义依据供检查。此动作不落盘。

`example.json`包含可运行的完整plan输入。`person.variant_confirmed`只有严格布尔true才选择指定variant，否则输出全部候选。模板必须包含且只包含一次`{target}`；可额外使用`{device_key}`、`{label}`，不接受属性、索引、格式规格或转换器。取消模板不接受target。目标前缀也必须由variant显式设置。

```json
{"action":"verify_targets","expected":"2025550101","allowed_prefixes":["","0"],"plan":[]}
```

实际使用时将plan动作输出的`plan`数组传入。空计划无目标冲突不代表任何设备已配置；检查仅为数字一致性，不可据此自动拨号或宣布正式生效。

## 数据、来源与边界

这是格式转换工具，不是脱敏器；显式传入的个人内容会出现在结果中，调用方决定本地结果如何保存。最大名单5000项/组100项，设备100项，模板变体20项；全部操作在内存中完成。

来源符号与调整见PROVENANCE.md。没有读取或携带原HTML、真实名单、通信账号、公司设备/场景配置、原运营商命令、Excel默认路径、GUI/拨号/发送。原Excel界面与导入器未迁移；使用显式JSON代替固定列与公司采集口径。

本项目源码采用 MIT 许可证，见 LICENSE；作者字段不自动证明所有权。没有捆绑第三方代码、依赖、真实联系人或历史输出。

## 2026-11-08 候选修订

- 格式化只删除普通空格，不将内部换行、制表和Unicode分隔符拼成一个号码。

使用包内合成样例复跑；发布集合根目录的 `verify_release.py --project extra-contact-transform` 会依次执行测试和首次使用命令。原有版本的测试计数属于当时记录，本轮汇总以集合验证报告为准。
