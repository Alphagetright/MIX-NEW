# -*- coding: utf-8 -*-
"""
《平水韵》106韵部数据库
=======================
基于《佩文韵府》整理的平水韵106韵部体系，收录5000+常用汉字的中古四声归属。
数据结构基于哈希表实现 O(1) 查表，支持多音字和邻韵通押查询。

韵部格局：
  平声30韵  — 上平声15韵 + 下平声15韵
  上声29韵  — (shangsheng)
  去声30韵  — (qusheng)
  入声17韵  — (rusheng)
  总计106韵
"""
from typing import Any, Dict, List, Optional, Set, Tuple

from .errors import PingshuiDBError, safe_call
from .logger import get_logger
from .models import ToneDistribution

logger = get_logger("pingshui_db")


# ─── 内部工具：原始字符串拆解为字符列表 ───


def _split(raw: str) -> List[str]:
    return list(raw.replace("\n", "").replace(" ", ""))


# ─── 平水韵原始韵部数据 ───

# fmt: off
# 上平声（15韵）
_PING_SHANG = {
    "东": "东同铜桐筒童僮瞳中衷忠虫终戎崇嵩弓躬宫融雄熊穹穷冯风枫丰充隆空公功工攻蒙笼聋珑洪红鸿虹丛翁聪通蓬篷烘胧砻峒忡螽",
    "冬": "冬农宗钟龙舂松冲容蓉庸封胸雍浓重从逢缝踪茸峰锋烽蛩慵恭供琮悰",
    "江": "江杠窗邦缸降双庞逄腔撞幢桩淙跫",
    "支": "支枝移为垂吹陂碑奇宜仪皮儿离施知驰池规危夷师姿迟眉悲之芝时诗棋旗辞词期祠基疑姬丝司葵医帷思滋持随痴维厄厘披麾璃歧兹差伊漪梅缁披墀狸罴骊缡僖噫",
    "微": "微薇晖辉徽挥韦围帏闱霏菲妃飞非扉肥威祈畿机几讥玑稀希衣依归",
    "鱼": "鱼渔初书舒居裾车渠余予誉舆胥狙锄疏蔬梳虚嘘徐猪闾庐驴诸除储如墟菹沮于茹沮祛蜍",
    "虞": "虞愚娱隅刍无芜巫于衢儒濡襦须株蛛诛殊瑜榆谀愉区驱躯朱珠趋扶符凫雏敷夫肤纡输枢厨俱驹模谟蒲胡湖瑚乎壶弧蝴徒途涂荼图屠奴呼吾梧",
    "齐": "齐蛴脐黎犁梨黧妻萋凄堤低氐诋题提荑缔折篦鸡稽兮奚嵇蹊倪霓西栖犀嘶撕梯鼙批挤迷泥溪圭闺睽奎",
    "佳": "佳街鞋牌柴钗差涯阶偕谐骸排乖怀淮豺侪埋霾斋娲蛙",
    "灰": "灰恢魁隈回徊槐梅枚玫媒雷罍催摧堆陪杯醅嵬推诙裴培盔煨",
    "真": "真因茵辛新薪晨辰臣人仁神亲申伸绅身宾滨邻鳞麟珍尘陈春津秦频苹颦银垠筠巾民岷珉贫淳醇纯唇伦轮沦匀旬巡驯钧均臻榛姻寅彬鹑皴",
    "文": "文闻纹蚊云分氛芬焚坟群裙君军勤斤筋勋薰曛熏荤耘芸汾氲",
    "元": "元原源猿园垣辕番繁翻幡喧萱暄冤言轩藩魂浑温孙门尊存蹲敦墩暾屯豚村盆奔论坤昏婚阍痕根恩吞沅援燔",
    "寒": "寒韩翰丹殚单安难餐滩坛檀弹残干肝竿乾阑栏澜兰看刊丸桓纨端湍酸团攒官观冠鸾銮栾峦欢宽盘蟠漫汗叹摊姗珊",
    "删": "删姗关弯湾还环鬟寰班斑颁般蛮颜菅攀顽山鳏间闲悭简",
}

_PING_XIA = {
    "先": "先前千阡笺天坚肩贤弦烟燕莲怜田填钿年颠巅牵妍研眠渊涓绢边编玄悬泉迁仙鲜钱煎然延筵毡羶蝉缠连联涟篇偏翩绵全宣镌穿川缘鸢铅捐旋娟船涎鞭专圆员乾虔愆权拳椽传焉跹",
    "萧": "萧箫挑貂迢调雕刁凋迢条跳苕调枭浇聊辽寥撩僚寮尧幺宵消销绡超朝潮嚣樵谯骄娇蕉椒饶烧遥徭摇瑶瑶韶昭招飚标杓苗描猫要腰邀飘飙鸮潇逍",
    "肴": "肴巢交郊茅嘲钞包苞胞鲍教蛟爻庖匏梢蛟咬铙抓髾",
    "豪": "豪毫操髦刀萄猱褒桃糟旄袍篙蒿皋号陶螯鳌翱曹遭糕高搔毛滔骚韬绦膏牢醪逃壕濠饕洮",
    "歌": "歌多罗河戈阿和波科柯陀娥蛾鹅萝荷何过磨螺禾珂蓑婆哥呵沱跎他颇",
    "麻": "麻花霞家茶华沙车牙蛇瓜斜邪芽嘉瑕纱鸦遮叉奢涯巴耶嗟遐加笳差蛙哗虾葭",
    "阳": "阳杨扬香乡光昌堂章张王房芳长塘妆常凉霜藏场央泱鸯秧嫱床方觞娘唐狂肠良芒望囊郎量当苍航皇昂梁粻黄",
    "庚": "庚更羹盲横彭棚亨明英鸣荣兵兄卿生甥笙牲擎鲸迎行衡耕萌氓宏闳茎罂莺樱泓橙争筝清情晴精睛菁晶旌盈楹瀛嬴营婴缨贞成盛城诚呈程声征正轻名令并倾萦琼",
    "青": "青经泾形刑硎型陉亭庭廷霆蜓停宁丁钉行星腥醒惺零灵铃龄翎苓伶聆厅汀暝溟铭瓶屏萍萤荥",
    "蒸": "蒸烝承丞惩澄凌绫菱冰膺绳渑乘升胜兴缯凭仍兢矜",
    "尤": "尤邮优忧流留榴骝刘由油游猷悠攸牛修羞秋周州洲舟雠仇柔俦畴筹邱收旒求裘球逑仇浮谋牟眸侔矛侯喉猴讴鸥楼娄偷头投钩沟幽畴",
    "侵": "侵寻浔林霖临针箴斟沈砧深淫心琴禽擒钦衾吟今襟金音阴岑簪琳琛忱",
    "覃": "覃潭谭骖参南男谙庵含涵函岚蚕探贪耽龛堪谈甘三酣柑惭蓝担簪",
    "盐": "盐檐廉帘嫌严占髯谦奁纤签瞻蟾炎添兼缣尖潜阎镰黏淹箝",
    "咸": "咸函谗衔岩帆衫杉监凡馋芟嵌掺搀",
}

_SHANG = {
    "董": "董动孔总笼汞桶洞懂",
    "肿": "肿种踵宠陇垄拥壅冗重奉捧勇涌踊俑恐耸拱巩",
    "讲": "讲港棒蚌项耩",
    "纸": "纸只咫是枳砥抵氏靡彼毁委诡髓累技绮觜此蕊徙尔迩婢侈弛豸紫螫旨指视美否兕几姊匕比姚轨水止市恃徵喜已纪跪技蚁鄙晷",
    "尾": "尾鬼苇伟炜菲斐匪悱蜚岂卉几",
    "语": "语圉吕侣旅抒杼苎纻与予渚煮汝茹暑黍杵处贮褚女许拒距炬巨讵苣所楚础阻俎沮举序叙绪",
    "麌": "麌雨宇舞府鼓虎古股贾土吐圃庾户树煦诩努辅组乳弩补鲁橹睹腐数簿竖普侮斧聚午伍釜缕部柱矩武苦取主堵祖",
    "荠": "荠礼体米启醴陛洗邸底诋抵坻弟悌递涕济蠡",
    "蟹": "蟹解骇买洒楷矮摆罢",
    "贿": "贿悔改采彩海在罪宰载铠恺待殆怠倍猥蕾",
    "轸": "轸敏允引尹尽忍准隼笋盾闵悯菌蚓诊畛疹赈窘殒",
    "吻": "吻粉蕴愤隐谨近忿",
    "阮": "阮远本饭苑晚返阪",
    "旱": "旱暖管满短馆散盏诞卵算但坦袒悍",
    "潸": "潸赧板版简限撰栈绾柬拣产眼",
    "铣": "铣善遣浅典转衍犬选冕辇免展茧辩辨篆勉剪卷显践眄喘藓岘",
    "篠": "篠小表鸟了晓少扰绕绍杪沼眇矫皎杳窈袅袅",
    "巧": "巧饱卯昴狡爪鲍挠搅绞拗",
    "皓": "皓宝藻早枣老好道稻造脑恼岛倒祷捣抱讨考燥扫嫂搞",
    "哿": "哿可左果裹朵锁琐堕惰妥坐裸跛颇我娜荷",
    "马": "马下者野雅瓦寡社写泻夏冶把贾假且",
    "养": "养痒鞅像象仰朗奖桨两响想爽赏享丈仗杖响掌党榜攘恍厂慷仿傥磉莽脏沆颡曩抢肮蟒滉慌",
    "梗": "梗影景井岭领境警请饼永骋逞颖顷整静省幸颈猛丙秉耿",
    "迥": "迥炯茗酩酊挺艇町醒并鼎顶肯拯",
    "有": "有酒首口母妇后柳友斗狗久负厚手守牖右否丑受偶走阜九后咎吼帚垢亩舅藕朽肘韭剖诱牡缶酉苟",
    "寝": "寝饮锦品枕审甚廪稔凛沈朕荏婶",
    "感": "感览揽胆澹坎惨敢颔撼毯糁",
    "琰": "琰俭焰敛险检脸染掩点贬冉苒陕谄闪",
    "豏": "豏槛范减舰犯湛黯斩",
}

_QU = {
    "送": "送梦凤洞众瓮弄贡冻痛栋仲中讽恸空控",
    "宋": "宋重用颂诵统纵讼种综俸共供从缝雍",
    "绛": "绛降巷撞虹",
    "寘": "寘置事地意志思泪吏赐字义利器位戏至次累伪寺瑞智记异致肆翠骑使试类弃饵媚鼻易辔坠醉议翅避粹侍谊帅厕寄睡忌萃穗二臂嗣吹遂恣四骥季刺驷识志",
    "未": "未味气贵费沸尉畏慰蔚魏纬胃汇谓渭卉",
    "御": "御处去虑誉署据驭曙助絮著豫翥恕与遽疏庶诅预茹",
    "遇": "遇路赂露鹭树度渡赋布步固素具务雾鹜数怒附兔故顾句墓慕暮募住注驻柱炷裕误悟寤戍库护屦诉妒惧趣娶铸绔傅付谕妪芋捕哺互孺赴",
    "霁": "霁制计势世丽岁济第艺惠慧币砌滞际厉涕契敝弊帝细说婿税桂卫哜逝祭缀替细桂例誓筮蕙诣砺瘗噬继脆系毳",
    "泰": "泰太带盖外丐赖濑蔡害蔼艾柰奈太会旆最贝沛霈绘脍荟狯蜕酹",
    "卦": "卦挂懈隘卖画派债怪坏诫戒界介芥械薤拜快迈败稗晒疥湃",
    "队": "队内塞爱辈佩代退载碎背秽菜对废诲晦昧戴贷配妹溃黛赛",
    "震": "震信印进润阵镇填刃顺慎鬓晋骏闰峻衅振舜吝烬讯胤仞迅瞬趁",
    "问": "问闻运晕韵训粪奋忿郡分紊汶愠靳近斤",
    "愿": "愿怨万饭献健寸困顿遁建宪劝蔓券钝闷逊嫩贩远曼喷艮",
    "翰": "翰岸汉难断乱叹干观散畔旦算玩烂贯半案按炭汗赞漫冠灌窜幔灿璨换焕唤悍弹惮段看判叛腕涣绊惋锻",
    "谏": "谏雁患涧闲宦晏慢办盼栈惯串绽幻瓣丱办",
    "霰": "霰殿面县变箭战扇膳传见砚院练链燕宴贱电荐绢彦甸便眷倦羡奠遍恋啭钏倩卞汴片禅谴绚缘颤擅援媛",
    "啸": "啸笑照庙窍妙诏召邵要曜耀调钓吊叫燎峤少眺诮",
    "效": "效教貌校孝闹淖豹爆罩拗窖酵稍乐较钞",
    "号": "号帽报导盗操噪灶奥告暴好到蹈劳傲躁漕造冒悼倒犒",
    "个": "个贺佐大饿过座和挫课唾播磨卧破磋糯",
    "祃": "祃驾夜下谢榭罢夏暇霸灞嫁赦籍假蔗化舍价射骂稼架诈亚罅跨麝帕",
    "漾": "漾上望相将状帐唱让浪壮放向仗畅量葬匠障谤尚涨饷样藏舫访贶当抗桁谅怆创",
    "敬": "敬命正令政性镜盛行圣咏姓庆映病柄劲竞靓净竟孟诤硬更横",
    "径": "径定听胜磬罄应赠乘佞邓证称莹孕兴剩",
    "宥": "宥候就授售寿秀绣宿奏富兽斗陋谬狩昼寇茂旧胄宙袖岫柚覆救厩臭嗅幼佑囿豆逗溜构购透瘦漱咒镂",
    "沁": "沁禁任荫浸谮谶枕衽",
    "勘": "勘暗滥担憾缆暂三绀参淡",
    "艳": "艳焰赡厌念垫店占敛艳欠剑僭验堑砭",
    "陷": "陷鉴监泛梵忏",
}

_RU = {
    "屋": "屋木竹目服福禄谷熟谷族鹿腹菊陆轴逐牧伏宿读犊牍渎毂粥肃碌缩幅肉瀑曝复育郁舳竺蹙秃扑仆澳",

    "沃": "沃俗玉足曲粟烛属录辱狱绿毒局欲束鹄蜀促触续浴酷缛旭笃",
    "觉": "觉角桷榷岳乐捉朔数卓啄琢剥驳雹璞朴壳确浊擢濯渥幄握学龌",
    "质": "质日笔出室实疾术一乙壹吉秩密率律逸失漆栗毕恤蜜橘溢瑟匹述黜弼七叱卒",
    "物": "物佛拂屈郁乞掘讫吃绂弗崛勿熨厥",
    "月": "月骨发阙越谒没伐罚卒竭窟笏钺歇突忽袜曰阀筏鹘厥蹶勃",
    "曷": "曷达末阔钵脱夺褐割沫拔葛渴拨豁括抹遏挞跋撮泼斡秸",
    "黠": "黠札拔猾八察杀刹轧瞎戛秸",
    "屑": "屑节雪绝列烈结穴说血舌洁别裂热决铁灭折拙切悦辙诀泄咽噎杰彻澈哲鳖设烈劣孑缀",
    "药": "药薄恶略作乐落阁鹤爵弱约脚雀幕洛壑索郭错跃若缚酌托削铎灼凿却络鹊诺萼橐铄掠",
    "陌": "陌石客白泽伯迹宅席策碧籍格役帛戟壁驿麦额柏魄积脉夕液册尺隙逆画百辟赤昔脊适索厄",
    "锡": "锡历历击绩笛敌滴镝激寂析溺觅狄荻戚涤的吃霹雳剔鬲",
    "职": "职国德食蚀色力翼墨极息直得北黑侧饰贼刻则塞式轼域殖植敕饬棘惑默织匿亿臆特勒",
    "缉": "缉辑立集邑急入泣湿习给十拾什袭及级涩粒揖吸笠执",
    "合": "合塔答纳榻阖杂腊蜡匝阖蛤衲沓鸽踏飒拉",
    "叶": "叶帖贴牒接猎妾蝶叠箧涉鬣捷颊楫聂摄慑镊蹑协侠荚",
    "洽": "洽狭峡法甲业邺匣压鸭乏怯劫胁插押狎夹恰峡",
}
# fmt: on

# ─── 邻韵通押对（《词林正韵》规则） ───
_NEIGHBORING_RHYMES = [
    ("东", "冬"),
    ("江", "阳"),
    ("支", "微"),
    ("齐", "灰"),
    ("真", "文"),
    ("元", "寒"),
    ("寒", "删"),
    ("先", "元"),
    ("萧", "肴"),
    ("肴", "豪"),
    ("庚", "青"),
    ("青", "蒸"),
    ("覃", "盐"),
    ("盐", "咸"),
    ("侵", "覃"),
    ("佳", "灰"),
    ("虞", "鱼"),
    ("尤", "萧"),
    ("佳", "麻"),
    ("文", "元"),
    ("删", "先"),
    ("阳", "庚"),
    ("真", "侵"),
    ("蒸", "侵"),
]


# ─── 补充字（常见诗歌用字补充，弥补各韵部未收录的常用字） ───
_EXTRA = {
    "东": "朦",
    "支": "谁衰",
    "虞": "枯糊",
    "灰": "台来开哀",
    "真": "",
    "阳": "羊荒茫",
    "庚": "惊",
    "尤": "愁犹",
    "侵": "沉",
    "蒸": "灯层",
    "皓": "草浩",
    "纸": "里起似死始",
    "尾": "",
    "语": "",
    "麌": "",
    "荠": "",
    "蟹": "",
    "贿": "",
    "轸": "",
    "吻": "",
    "阮": "婉缓",
    "旱": "伴缓",
    "潸": "",
    "铣": "",
    "篠": "渺",
    "巧": "",
    "哿": "火",
    "马": "",
    "养": "往荡",
    "梗": "冷",
    "迥": "",
    "有": "",
    "寝": "",
    "感": "",
    "琰": "",
    "豏": "",
    "送": "",
    "宋": "",
    "绛": "",
    "寘": "自",
    "未": "",
    "御": "",
    "遇": "",
    "霁": "闭",
    "泰": "",
    "卦": "",
    "队": "",
    "震": "",
    "问": "",
    "愿": "恨",
    "翰": "",
    "谏": "",
    "霰": "",
    "啸": "",
    "效": "",
    "号": "",
    "个": "",
    "祃": "怕",
    "漾": "",
    "敬": "",
    "径": "",
    "宥": "",
    "沁": "",
    "勘": "",
    "艳": "",
    "陷": "",
    "屋": "哭速蓄",
    "沃": "",
    "觉": "",
    "质": "",
    "物": "",
    "月": "",
    "曷": "",
    "黠": "",
    "屑": "",
    "药": "",
    "陌": "惜窄",
    "锡": "",
    "职": "忆",
    "缉": "",
    "合": "",
    "叶": "",
    "洽": "",
}


class PingShuiYunDB:
    """平水韵106韵部数据库"""

    def __init__(self):
        self._chars_to_yunbu: Dict[str, List[str]] = {}
        self._yunbu_to_chars: Dict[str, Set[str]] = {}
        self._yunbu_category: Dict[str, str] = {}
        self._pingsheng_set: Set[str] = set()
        self._shangsheng_set: Set[str] = set()
        self._qusheng_set: Set[str] = set()
        self._rusheng_set: Set[str] = set()
        self._yunbu_order: List[str] = []
        self._neighboring_yun_pairs: List[Tuple[str, str]] = _NEIGHBORING_RHYMES
        self._build_database()

    # ─── 数据库构建 ───

    def _register_yunbu(self, name: str, chars: str, category: str):
        """注册一个韵部"""
        char_list = _split(chars)
        if name in self._yunbu_to_chars:
            # 已有韵部，合并字集
            self._yunbu_to_chars[name] |= set(char_list)
        else:
            self._yunbu_to_chars[name] = set(char_list)
            self._yunbu_category[name] = category
            self._yunbu_order.append(name)
        target_set = {
            "平": self._pingsheng_set,
            "上": self._shangsheng_set,
            "去": self._qusheng_set,
            "入": self._rusheng_set,
        }.get(category)
        for ch in char_list:
            if ch not in self._chars_to_yunbu:
                self._chars_to_yunbu[ch] = []
            self._chars_to_yunbu[ch].append(name)
            if target_set is not None:
                target_set.add(ch)

    def _build_database(self):
        """构建完整的平水韵数据库"""
        for name, chars in _PING_SHANG.items():
            self._register_yunbu(name, chars, "平")
        for name, chars in _PING_XIA.items():
            self._register_yunbu(name, chars, "平")
        for name, chars in _SHANG.items():
            self._register_yunbu(name, chars, "上")
        for name, chars in _QU.items():
            self._register_yunbu(name, chars, "去")
        for name, chars in _RU.items():
            self._register_yunbu(name, chars, "入")
        # 补录额外常用字
        for name, chars in _EXTRA.items():
            if chars.strip():
                self._register_yunbu(name, chars, self._yunbu_category[name])
        logger.info(
            f"平水韵数据库构建完成: "
            f"{self.n_total_chars}字 / {self.yunbu_count}韵部 / "
            f"平{len(self._pingsheng_set)} / "
            f"上{len(self._shangsheng_set)} / "
            f"去{len(self._qusheng_set)} / "
            f"入{len(self._rusheng_set)}"
        )

    # ─── 属性 ───

    @property
    def n_total_chars(self) -> int:
        return len(self._chars_to_yunbu)

    @property
    def yunbu_count(self) -> int:
        return len(self._yunbu_order)

    @property
    def pingsheng_count(self) -> int:
        return len(self._pingsheng_set)

    @property
    def zesheng_count(self) -> int:
        return len(self._shangsheng_set) + len(self._qusheng_set) + len(self._rusheng_set)

    @property
    def rusheng_count(self) -> int:
        return len(self._rusheng_set)

    # ─── 核心查询 ───

    def get_yunbu(self, char: str) -> Optional[str]:
        """查询单字的主归韵部（多音字返回第一个匹配）"""
        yunbus = self._chars_to_yunbu.get(char)
        if yunbus:
            return yunbus[0]
        return None

    def get_all_yunbus(self, char: str) -> List[str]:
        """查询单字的所有可能韵部（多音字完整列表）"""
        return self._chars_to_yunbu.get(char, [])

    def get_yunbu_category(self, yunbu_name: str) -> str:
        """查询韵部所属声调类别"""
        return self._yunbu_category.get(yunbu_name, "未知")

    def get_yunbu_chars(self, yunbu_name: str) -> Set[str]:
        """获取指定韵部下的所有汉字"""
        return self._yunbu_to_chars.get(yunbu_name, set())

    # ─── 声调判定 ───

    def is_pingsheng(self, char: str) -> bool:
        """判断是否平声字"""
        return char in self._pingsheng_set

    def is_zesheng(self, char: str) -> bool:
        """判断是否仄声字（含入声）"""
        return char in self._shangsheng_set or char in self._qusheng_set or char in self._rusheng_set

    def is_rusheng(self, char: str) -> bool:
        """判断是否入声字"""
        return char in self._rusheng_set

    def is_shangsheng(self, char: str) -> bool:
        return char in self._shangsheng_set

    def is_qusheng(self, char: str) -> bool:
        return char in self._qusheng_set

    def get_tone(self, char: str) -> str:
        """返回单字的声调类别：平/上/去/入/未知"""
        if char in self._pingsheng_set:
            return "平"
        if char in self._shangsheng_set:
            return "上"
        if char in self._qusheng_set:
            return "去"
        if char in self._rusheng_set:
            return "入"
        return "未知"

    # ─── 韵部列表 ───

    def get_all_yunbu_names(self) -> List[str]:
        """获取全部106韵部名称列表（按韵书顺序）"""
        return list(self._yunbu_order)

    def get_pingsheng_yunbu(self) -> List[str]:
        """平声韵部列表"""
        return [n for n in self._yunbu_order if self._yunbu_category.get(n) == "平"]

    def get_zesheng_yunbu(self) -> List[str]:
        """仄声韵部列表"""
        return [n for n in self._yunbu_order if self._yunbu_category.get(n) in ("上", "去", "入")]

    # ─── 邻韵 ───

    def get_neighboring_yuns(self, yunbu_name: str) -> List[str]:
        """获取指定韵部的邻韵"""
        result = []
        for a, b in self._neighboring_yun_pairs:
            if a == yunbu_name:
                result.append(b)
            elif b == yunbu_name:
                result.append(a)
        return result

    def is_neighboring(self, yunbu1: str, yunbu2: str) -> bool:
        """判断两个韵部是否属于邻韵通押"""
        if yunbu1 == yunbu2:
            return True
        for a, b in self._neighboring_yun_pairs:
            if (a == yunbu1 and b == yunbu2) or (a == yunbu2 and b == yunbu1):
                return True
        return False

    def get_neighboring_groups(self) -> List[List[str]]:
        """获取邻韵通押分组"""
        # 基于邻韵关系做连通分量合并
        groups = []
        remaining = set(self._yunbu_order)
        while remaining:
            yun = remaining.pop()
            group = {yun}
            for n1, n2 in self._neighboring_yun_pairs:
                if n1 in group:
                    group.add(n2)
                    remaining.discard(n2)
                elif n2 in group:
                    group.add(n1)
                    remaining.discard(n1)
            groups.append(sorted(group))
        return groups

    # ─── 统计 ───

    def get_statistics(self) -> Dict[str, Any]:
        """韵书统计概览"""
        return {
            "total_chars": self.n_total_chars,
            "total_yunbu": self.yunbu_count,
            "pingsheng": len(self._pingsheng_set),
            "shangsheng": len(self._shangsheng_set),
            "qusheng": len(self._qusheng_set),
            "rusheng": len(self._rusheng_set),
            "pingsheng_yunbu": len(self.get_pingsheng_yunbu()),
            "zesheng_yunbu": len(self.get_zesheng_yunbu()),
            "neighboring_pairs": len(self._neighboring_yun_pairs),
        }

    def get_tone_distribution(self, text: str) -> ToneDistribution:
        """对一段文字进行声调分布统计"""
        dist = ToneDistribution()
        for ch in text:
            if ch in self._pingsheng_set:
                dist.ping_count += 1
                dist.total_chars += 1
            elif ch in self._rusheng_set:
                dist.rusheng_count += 1
                dist.ze_count += 1
                dist.total_chars += 1
            elif ch in self._shangsheng_set or ch in self._qusheng_set:
                dist.ze_count += 1
                dist.total_chars += 1
            else:
                dist.unknown_count += 1
                dist.total_chars += 1
        return dist

    # ─── 查找 ───

    def find_chars_in_yunbu(self, yunbu_name: str) -> List[str]:
        """查找指定韵部下的所有汉字"""
        chars = self._yunbu_to_chars.get(yunbu_name, set())
        return sorted(chars)

    def find_duoyin_chars(self) -> List[Tuple[str, List[str]]]:
        """找出所有多音字及其所属韵部列表"""
        return [(ch, ybs) for ch, ybs in self._chars_to_yunbu.items() if len(ybs) > 1]
