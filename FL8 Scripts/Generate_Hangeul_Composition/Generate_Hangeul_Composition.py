#FLM: MW: Generate Hangeul Composition

import re, string

import FL as legacy
from fontgate import fgNametable
import fontlab as fl6
from typerig.proxy.fl.objects.font import * 

from typerig.proxy.fl.gui.widgets import *
from typerig.proxy.fl.gui import QtGui
from PythonQt import QtCore

app_version = '1.10'
app_name = 'Minwoo | Generate Hangeul Composition'
qapp = QtGui.QApplication.instance()
nt = fgNametable()
flP = fl6.flPackage(fl6.CurrentFont())


################################################################################
# Hangul Unicode Variables
# Base code forked from Hangulpy
# https://github.com/rhobot/Hangulpy
################################################################################

class NotHangulException(Exception):
    pass

class NotHangulException(Exception):
    pass

class NotLetterException(Exception):
    pass

CHO = (
    u'ㄱ', u'ㄲ', u'ㄴ', u'ㄷ', u'ㄸ', u'ㄹ', u'ㅁ', u'ㅂ', u'ㅃ', u'ㅅ',
    u'ㅆ', u'ㅇ', u'ㅈ', u'ㅉ', u'ㅊ', u'ㅋ', u'ㅌ', u'ㅍ', u'ㅎ'
)

JUNG = (
    u'ㅏ', u'ㅐ', u'ㅑ', u'ㅒ', u'ㅓ', u'ㅔ', u'ㅕ', u'ㅖ', u'ㅗ', u'ㅘ',
    u'ㅙ', u'ㅚ', u'ㅛ', u'ㅜ', u'ㅝ', u'ㅞ', u'ㅟ', u'ㅠ', u'ㅡ', u'ㅢ', u'ㅣ'
)

JUNG_BY_TYPE = (
    u'ㅏ', u'ㅑ', u'ㅓ', u'ㅕ', u'ㅣ', u'ㅐ', u'ㅒ', u'ㅔ', u'ㅖ', u'ㅗ',
    u'ㅛ', u'ㅜ', u'ㅠ', u'ㅡ', u'ㅘ', u'ㅚ', u'ㅢ', u'ㅙ', u'ㅝ', u'ㅟ', u'ㅞ'
)

JONG = (
    u'', u'ㄱ', u'ㄲ', u'ㄳ', u'ㄴ', u'ㄵ', u'ㄶ', u'ㄷ', u'ㄹ', u'ㄺ',
    u'ㄻ', u'ㄼ', u'ㄽ', u'ㄾ', u'ㄿ', u'ㅀ', u'ㅁ', u'ㅂ', u'ㅄ', u'ㅅ',
    u'ㅆ', u'ㅇ', u'ㅈ', u'ㅊ', u'ㅋ', u'ㅌ', u'ㅍ', u'ㅎ'
)
JAMO_LIST = [CHO, JUNG, JONG]

JAMO_LABEL_KO = [u'초성', u'중성', u'종성']
JAMO_LABEL_EN = [u'cho', u'jung', u'jong']

JAMO = CHO + JUNG + JONG[1:]

NUM_CHO = 19
NUM_JUNG = 21
NUM_JONG = 28

FIRST_HANGUL_UNICODE = 0xAC00  # '가'
LAST_HANGUL_UNICODE = 0xD7A3  # '힣'

global SORT_ORDER, CHAR_RANGE
SORT_ORDER = 0  
# 0: 초성순(=유니코드순) // 1: 중성순 // 2: 종성순

CHAR_RANGE = 0 
# 0: ADOBE KR9 2780자 // 1: KSX1001 2350자 // 2: 11172자 // 3: 8392자

SORT_JUNG_BY_TYPE = False
LINE_BREAK = False

KSX_1001 = [
u"가",u"각",u"간",u"갇",u"갈",u"갉",u"갊",u"감",u"갑",u"값",u"갓",u"갔",u"강",u"갖",u"갗",u"같",u"갚",u"갛",u"개",u"객",u"갠",u"갤",u"갬",u"갭",u"갯",u"갰",u"갱",u"갸",u"갹",u"갼",u"걀",u"걋",u"걍",u"걔",u"걘",u"걜",u"거",u"걱",u"건",u"걷",u"걸",u"걺",u"검",u"겁",u"것",u"겄",u"겅",u"겆",u"겉",u"겊",u"겋",u"게",u"겐",u"겔",u"겜",u"겝",u"겟",u"겠",u"겡",u"겨",u"격",u"겪",u"견",u"겯",u"결",u"겸",u"겹",u"겻",u"겼",u"경",u"곁",u"계",u"곈",u"곌",u"곕",u"곗",u"고",u"곡",u"곤",u"곧",u"골",u"곪",u"곬",u"곯",u"곰",u"곱",u"곳",u"공",u"곶",u"과",u"곽",u"관",u"괄",u"괆",u"괌",u"괍",u"괏",u"광",u"괘",u"괜",u"괠",u"괩",u"괬",u"괭",u"괴",u"괵",u"괸",u"괼",u"굄",u"굅",u"굇",u"굉",u"교",u"굔",u"굘",u"굡",u"굣",u"구",u"국",u"군",u"굳",u"굴",u"굵",u"굶",u"굻",u"굼",u"굽",u"굿",u"궁",u"궂",u"궈",u"궉",u"권",u"궐",u"궜",u"궝",u"궤",u"궷",u"귀",u"귁",u"귄",u"귈",u"귐",u"귑",u"귓",u"규",u"균",u"귤",u"그",u"극",u"근",u"귿",u"글",u"긁",u"금",u"급",u"긋",u"긍",u"긔",u"기",u"긱",u"긴",u"긷",u"길",u"긺",u"김",u"깁",u"깃",u"깅",u"깆",u"깊",u"까",u"깍",u"깎",u"깐",u"깔",u"깖",u"깜",u"깝",u"깟",u"깠",u"깡",u"깥",u"깨",u"깩",u"깬",u"깰",u"깸",u"깹",u"깻",u"깼",u"깽",u"꺄",u"꺅",u"꺌",u"꺼",u"꺽",u"꺾",u"껀",u"껄",u"껌",u"껍",u"껏",u"껐",u"껑",u"께",u"껙",u"껜",u"껨",u"껫",u"껭",u"껴",u"껸",u"껼",u"꼇",u"꼈",u"꼍",u"꼐",u"꼬",u"꼭",u"꼰",u"꼲",u"꼴",u"꼼",u"꼽",u"꼿",u"꽁",u"꽂",u"꽃",u"꽈",u"꽉",u"꽐",u"꽜",u"꽝",u"꽤",u"꽥",u"꽹",u"꾀",u"꾄",u"꾈",u"꾐",u"꾑",u"꾕",u"꾜",u"꾸",u"꾹",u"꾼",u"꿀",u"꿇",u"꿈",u"꿉",u"꿋",u"꿍",u"꿎",u"꿔",u"꿜",u"꿨",u"꿩",u"꿰",u"꿱",u"꿴",u"꿸",u"뀀",u"뀁",u"뀄",u"뀌",u"뀐",u"뀔",u"뀜",u"뀝",u"뀨",u"끄",u"끅",u"끈",u"끊",u"끌",u"끎",u"끓",u"끔",u"끕",u"끗",u"끙",u"끝",u"끼",u"끽",u"낀",u"낄",u"낌",u"낍",u"낏",u"낑",u"나",u"낙",u"낚",u"난",u"낟",u"날",u"낡",u"낢",u"남",u"납",u"낫",u"났",u"낭",u"낮",u"낯",u"낱",u"낳",u"내",u"낵",u"낸",u"낼",u"냄",u"냅",u"냇",u"냈",u"냉",u"냐",u"냑",u"냔",u"냘",u"냠",u"냥",u"너",u"넉",u"넋",u"넌",u"널",u"넒",u"넓",u"넘",u"넙",u"넛",u"넜",u"넝",u"넣",u"네",u"넥",u"넨",u"넬",u"넴",u"넵",u"넷",u"넸",u"넹",u"녀",u"녁",u"년",u"녈",u"념",u"녑",u"녔",u"녕",u"녘",u"녜",u"녠",u"노",u"녹",u"논",u"놀",u"놂",u"놈",u"놉",u"놋",u"농",u"높",u"놓",u"놔",u"놘",u"놜",u"놨",u"뇌",u"뇐",u"뇔",u"뇜",u"뇝",u"뇟",u"뇨",u"뇩",u"뇬",u"뇰",u"뇹",u"뇻",u"뇽",u"누",u"눅",u"눈",u"눋",u"눌",u"눔",u"눕",u"눗",u"눙",u"눠",u"눴",u"눼",u"뉘",u"뉜",u"뉠",u"뉨",u"뉩",u"뉴",u"뉵",u"뉼",u"늄",u"늅",u"늉",u"느",u"늑",u"는",u"늘",u"늙",u"늚",u"늠",u"늡",u"늣",u"능",u"늦",u"늪",u"늬",u"늰",u"늴",u"니",u"닉",u"닌",u"닐",u"닒",u"님",u"닙",u"닛",u"닝",u"닢",u"다",u"닥",u"닦",u"단",u"닫",u"달",u"닭",u"닮",u"닯",u"닳",u"담",u"답",u"닷",u"닸",u"당",u"닺",u"닻",u"닿",u"대",u"댁",u"댄",u"댈",u"댐",u"댑",u"댓",u"댔",u"댕",u"댜",u"더",u"덕",u"덖",u"던",u"덛",u"덜",u"덞",u"덟",u"덤",u"덥",u"덧",u"덩",u"덫",u"덮",u"데",u"덱",u"덴",u"델",u"뎀",u"뎁",u"뎃",u"뎄",u"뎅",u"뎌",u"뎐",u"뎔",u"뎠",u"뎡",u"뎨",u"뎬",u"도",u"독",u"돈",u"돋",u"돌",u"돎",u"돐",u"돔",u"돕",u"돗",u"동",u"돛",u"돝",u"돠",u"돤",u"돨",u"돼",u"됐",u"되",u"된",u"될",u"됨",u"됩",u"됫",u"됴",u"두",u"둑",u"둔",u"둘",u"둠",u"둡",u"둣",u"둥",u"둬",u"뒀",u"뒈",u"뒝",u"뒤",u"뒨",u"뒬",u"뒵",u"뒷",u"뒹",u"듀",u"듄",u"듈",u"듐",u"듕",u"드",u"득",u"든",u"듣",u"들",u"듦",u"듬",u"듭",u"듯",u"등",u"듸",u"디",u"딕",u"딘",u"딛",u"딜",u"딤",u"딥",u"딧",u"딨",u"딩",u"딪",u"따",u"딱",u"딴",u"딸",u"땀",u"땁",u"땃",u"땄",u"땅",u"땋",u"때",u"땍",u"땐",u"땔",u"땜",u"땝",u"땟",u"땠",u"땡",u"떠",u"떡",u"떤",u"떨",u"떪",u"떫",u"떰",u"떱",u"떳",u"떴",u"떵",u"떻",u"떼",u"떽",u"뗀",u"뗄",u"뗌",u"뗍",u"뗏",u"뗐",u"뗑",u"뗘",u"뗬",u"또",u"똑",u"똔",u"똘",u"똥",u"똬",u"똴",u"뙈",u"뙤",u"뙨",u"뚜",u"뚝",u"뚠",u"뚤",u"뚫",u"뚬",u"뚱",u"뛔",u"뛰",u"뛴",u"뛸",u"뜀",u"뜁",u"뜅",u"뜨",u"뜩",u"뜬",u"뜯",u"뜰",u"뜸",u"뜹",u"뜻",u"띄",u"띈",u"띌",u"띔",u"띕",u"띠",u"띤",u"띨",u"띰",u"띱",u"띳",u"띵",u"라",u"락",u"란",u"랄",u"람",u"랍",u"랏",u"랐",u"랑",u"랒",u"랖",u"랗",u"래",u"랙",u"랜",u"랠",u"램",u"랩",u"랫",u"랬",u"랭",u"랴",u"략",u"랸",u"럇",u"량",u"러",u"럭",u"런",u"럴",u"럼",u"럽",u"럿",u"렀",u"렁",u"렇",u"레",u"렉",u"렌",u"렐",u"렘",u"렙",u"렛",u"렝",u"려",u"력",u"련",u"렬",u"렴",u"렵",u"렷",u"렸",u"령",u"례",u"롄",u"롑",u"롓",u"로",u"록",u"론",u"롤",u"롬",u"롭",u"롯",u"롱",u"롸",u"롼",u"뢍",u"뢨",u"뢰",u"뢴",u"뢸",u"룀",u"룁",u"룃",u"룅",u"료",u"룐",u"룔",u"룝",u"룟",u"룡",u"루",u"룩",u"룬",u"룰",u"룸",u"룹",u"룻",u"룽",u"뤄",u"뤘",u"뤠",u"뤼",u"뤽",u"륀",u"륄",u"륌",u"륏",u"륑",u"류",u"륙",u"륜",u"률",u"륨",u"륩",u"륫",u"륭",u"르",u"륵",u"른",u"를",u"름",u"릅",u"릇",u"릉",u"릊",u"릍",u"릎",u"리",u"릭",u"린",u"릴",u"림",u"립",u"릿",u"링",u"마",u"막",u"만",u"많",u"맏",u"말",u"맑",u"맒",u"맘",u"맙",u"맛",u"망",u"맞",u"맡",u"맣",u"매",u"맥",u"맨",u"맬",u"맴",u"맵",u"맷",u"맸",u"맹",u"맺",u"먀",u"먁",u"먈",u"먕",u"머",u"먹",u"먼",u"멀",u"멂",u"멈",u"멉",u"멋",u"멍",u"멎",u"멓",u"메",u"멕",u"멘",u"멜",u"멤",u"멥",u"멧",u"멨",u"멩",u"며",u"멱",u"면",u"멸",u"몃",u"몄",u"명",u"몇",u"몌",u"모",u"목",u"몫",u"몬",u"몰",u"몲",u"몸",u"몹",u"못",u"몽",u"뫄",u"뫈",u"뫘",u"뫙",u"뫼",u"묀",u"묄",u"묍",u"묏",u"묑",u"묘",u"묜",u"묠",u"묩",u"묫",u"무",u"묵",u"묶",u"문",u"묻",u"물",u"묽",u"묾",u"뭄",u"뭅",u"뭇",u"뭉",u"뭍",u"뭏",u"뭐",u"뭔",u"뭘",u"뭡",u"뭣",u"뭬",u"뮈",u"뮌",u"뮐",u"뮤",u"뮨",u"뮬",u"뮴",u"뮷",u"므",u"믄",u"믈",u"믐",u"믓",u"미",u"믹",u"민",u"믿",u"밀",u"밂",u"밈",u"밉",u"밋",u"밌",u"밍",u"및",u"밑",u"바",u"박",u"밖",u"밗",u"반",u"받",u"발",u"밝",u"밞",u"밟",u"밤",u"밥",u"밧",u"방",u"밭",u"배",u"백",u"밴",u"밸",u"뱀",u"뱁",u"뱃",u"뱄",u"뱅",u"뱉",u"뱌",u"뱍",u"뱐",u"뱝",u"버",u"벅",u"번",u"벋",u"벌",u"벎",u"범",u"법",u"벗",u"벙",u"벚",u"베",u"벡",u"벤",u"벧",u"벨",u"벰",u"벱",u"벳",u"벴",u"벵",u"벼",u"벽",u"변",u"별",u"볍",u"볏",u"볐",u"병",u"볕",u"볘",u"볜",u"보",u"복",u"볶",u"본",u"볼",u"봄",u"봅",u"봇",u"봉",u"봐",u"봔",u"봤",u"봬",u"뵀",u"뵈",u"뵉",u"뵌",u"뵐",u"뵘",u"뵙",u"뵤",u"뵨",u"부",u"북",u"분",u"붇",u"불",u"붉",u"붊",u"붐",u"붑",u"붓",u"붕",u"붙",u"붚",u"붜",u"붤",u"붰",u"붸",u"뷔",u"뷕",u"뷘",u"뷜",u"뷩",u"뷰",u"뷴",u"뷸",u"븀",u"븃",u"븅",u"브",u"븍",u"븐",u"블",u"븜",u"븝",u"븟",u"비",u"빅",u"빈",u"빌",u"빎",u"빔",u"빕",u"빗",u"빙",u"빚",u"빛",u"빠",u"빡",u"빤",u"빨",u"빪",u"빰",u"빱",u"빳",u"빴",u"빵",u"빻",u"빼",u"빽",u"뺀",u"뺄",u"뺌",u"뺍",u"뺏",u"뺐",u"뺑",u"뺘",u"뺙",u"뺨",u"뻐",u"뻑",u"뻔",u"뻗",u"뻘",u"뻠",u"뻣",u"뻤",u"뻥",u"뻬",u"뼁",u"뼈",u"뼉",u"뼘",u"뼙",u"뼛",u"뼜",u"뼝",u"뽀",u"뽁",u"뽄",u"뽈",u"뽐",u"뽑",u"뽕",u"뾔",u"뾰",u"뿅",u"뿌",u"뿍",u"뿐",u"뿔",u"뿜",u"뿟",u"뿡",u"쀼",u"쁑",u"쁘",u"쁜",u"쁠",u"쁨",u"쁩",u"삐",u"삑",u"삔",u"삘",u"삠",u"삡",u"삣",u"삥",u"사",u"삭",u"삯",u"산",u"삳",u"살",u"삵",u"삶",u"삼",u"삽",u"삿",u"샀",u"상",u"샅",u"새",u"색",u"샌",u"샐",u"샘",u"샙",u"샛",u"샜",u"생",u"샤",u"샥",u"샨",u"샬",u"샴",u"샵",u"샷",u"샹",u"섀",u"섄",u"섈",u"섐",u"섕",u"서",u"석",u"섞",u"섟",u"선",u"섣",u"설",u"섦",u"섧",u"섬",u"섭",u"섯",u"섰",u"성",u"섶",u"세",u"섹",u"센",u"셀",u"셈",u"셉",u"셋",u"셌",u"셍",u"셔",u"셕",u"션",u"셜",u"셤",u"셥",u"셧",u"셨",u"셩",u"셰",u"셴",u"셸",u"솅",u"소",u"속",u"솎",u"손",u"솔",u"솖",u"솜",u"솝",u"솟",u"송",u"솥",u"솨",u"솩",u"솬",u"솰",u"솽",u"쇄",u"쇈",u"쇌",u"쇔",u"쇗",u"쇘",u"쇠",u"쇤",u"쇨",u"쇰",u"쇱",u"쇳",u"쇼",u"쇽",u"숀",u"숄",u"숌",u"숍",u"숏",u"숑",u"수",u"숙",u"순",u"숟",u"술",u"숨",u"숩",u"숫",u"숭",u"숯",u"숱",u"숲",u"숴",u"쉈",u"쉐",u"쉑",u"쉔",u"쉘",u"쉠",u"쉥",u"쉬",u"쉭",u"쉰",u"쉴",u"쉼",u"쉽",u"쉿",u"슁",u"슈",u"슉",u"슐",u"슘",u"슛",u"슝",u"스",u"슥",u"슨",u"슬",u"슭",u"슴",u"습",u"슷",u"승",u"시",u"식",u"신",u"싣",u"실",u"싫",u"심",u"십",u"싯",u"싱",u"싶",u"싸",u"싹",u"싻",u"싼",u"쌀",u"쌈",u"쌉",u"쌌",u"쌍",u"쌓",u"쌔",u"쌕",u"쌘",u"쌜",u"쌤",u"쌥",u"쌨",u"쌩",u"썅",u"써",u"썩",u"썬",u"썰",u"썲",u"썸",u"썹",u"썼",u"썽",u"쎄",u"쎈",u"쎌",u"쏀",u"쏘",u"쏙",u"쏜",u"쏟",u"쏠",u"쏢",u"쏨",u"쏩",u"쏭",u"쏴",u"쏵",u"쏸",u"쐈",u"쐐",u"쐤",u"쐬",u"쐰",u"쐴",u"쐼",u"쐽",u"쑈",u"쑤",u"쑥",u"쑨",u"쑬",u"쑴",u"쑵",u"쑹",u"쒀",u"쒔",u"쒜",u"쒸",u"쒼",u"쓩",u"쓰",u"쓱",u"쓴",u"쓸",u"쓺",u"쓿",u"씀",u"씁",u"씌",u"씐",u"씔",u"씜",u"씨",u"씩",u"씬",u"씰",u"씸",u"씹",u"씻",u"씽",u"아",u"악",u"안",u"앉",u"않",u"알",u"앍",u"앎",u"앓",u"암",u"압",u"앗",u"았",u"앙",u"앝",u"앞",u"애",u"액",u"앤",u"앨",u"앰",u"앱",u"앳",u"앴",u"앵",u"야",u"약",u"얀",u"얄",u"얇",u"얌",u"얍",u"얏",u"양",u"얕",u"얗",u"얘",u"얜",u"얠",u"얩",u"어",u"억",u"언",u"얹",u"얻",u"얼",u"얽",u"얾",u"엄",u"업",u"없",u"엇",u"었",u"엉",u"엊",u"엌",u"엎",u"에",u"엑",u"엔",u"엘",u"엠",u"엡",u"엣",u"엥",u"여",u"역",u"엮",u"연",u"열",u"엶",u"엷",u"염",u"엽",u"엾",u"엿",u"였",u"영",u"옅",u"옆",u"옇",u"예",u"옌",u"옐",u"옘",u"옙",u"옛",u"옜",u"오",u"옥",u"온",u"올",u"옭",u"옮",u"옰",u"옳",u"옴",u"옵",u"옷",u"옹",u"옻",u"와",u"왁",u"완",u"왈",u"왐",u"왑",u"왓",u"왔",u"왕",u"왜",u"왝",u"왠",u"왬",u"왯",u"왱",u"외",u"왹",u"왼",u"욀",u"욈",u"욉",u"욋",u"욍",u"요",u"욕",u"욘",u"욜",u"욤",u"욥",u"욧",u"용",u"우",u"욱",u"운",u"울",u"욹",u"욺",u"움",u"웁",u"웃",u"웅",u"워",u"웍",u"원",u"월",u"웜",u"웝",u"웠",u"웡",u"웨",u"웩",u"웬",u"웰",u"웸",u"웹",u"웽",u"위",u"윅",u"윈",u"윌",u"윔",u"윕",u"윗",u"윙",u"유",u"육",u"윤",u"율",u"윰",u"윱",u"윳",u"융",u"윷",u"으",u"윽",u"은",u"을",u"읊",u"음",u"읍",u"읏",u"응",u"읒",u"읓",u"읔",u"읕",u"읖",u"읗",u"의",u"읜",u"읠",u"읨",u"읫",u"이",u"익",u"인",u"일",u"읽",u"읾",u"잃",u"임",u"입",u"잇",u"있",u"잉",u"잊",u"잎",u"자",u"작",u"잔",u"잖",u"잗",u"잘",u"잚",u"잠",u"잡",u"잣",u"잤",u"장",u"잦",u"재",u"잭",u"잰",u"잴",u"잼",u"잽",u"잿",u"쟀",u"쟁",u"쟈",u"쟉",u"쟌",u"쟎",u"쟐",u"쟘",u"쟝",u"쟤",u"쟨",u"쟬",u"저",u"적",u"전",u"절",u"젊",u"점",u"접",u"젓",u"정",u"젖",u"제",u"젝",u"젠",u"젤",u"젬",u"젭",u"젯",u"젱",u"져",u"젼",u"졀",u"졈",u"졉",u"졌",u"졍",u"졔",u"조",u"족",u"존",u"졸",u"졺",u"좀",u"좁",u"좃",u"종",u"좆",u"좇",u"좋",u"좌",u"좍",u"좔",u"좝",u"좟",u"좡",u"좨",u"좼",u"좽",u"죄",u"죈",u"죌",u"죔",u"죕",u"죗",u"죙",u"죠",u"죡",u"죤",u"죵",u"주",u"죽",u"준",u"줄",u"줅",u"줆",u"줌",u"줍",u"줏",u"중",u"줘",u"줬",u"줴",u"쥐",u"쥑",u"쥔",u"쥘",u"쥠",u"쥡",u"쥣",u"쥬",u"쥰",u"쥴",u"쥼",u"즈",u"즉",u"즌",u"즐",u"즘",u"즙",u"즛",u"증",u"지",u"직",u"진",u"짇",u"질",u"짊",u"짐",u"집",u"짓",u"징",u"짖",u"짙",u"짚",u"짜",u"짝",u"짠",u"짢",u"짤",u"짧",u"짬",u"짭",u"짯",u"짰",u"짱",u"째",u"짹",u"짼",u"쨀",u"쨈",u"쨉",u"쨋",u"쨌",u"쨍",u"쨔",u"쨘",u"쨩",u"쩌",u"쩍",u"쩐",u"쩔",u"쩜",u"쩝",u"쩟",u"쩠",u"쩡",u"쩨",u"쩽",u"쪄",u"쪘",u"쪼",u"쪽",u"쫀",u"쫄",u"쫌",u"쫍",u"쫏",u"쫑",u"쫓",u"쫘",u"쫙",u"쫠",u"쫬",u"쫴",u"쬈",u"쬐",u"쬔",u"쬘",u"쬠",u"쬡",u"쭁",u"쭈",u"쭉",u"쭌",u"쭐",u"쭘",u"쭙",u"쭝",u"쭤",u"쭸",u"쭹",u"쮜",u"쮸",u"쯔",u"쯤",u"쯧",u"쯩",u"찌",u"찍",u"찐",u"찔",u"찜",u"찝",u"찡",u"찢",u"찧",u"차",u"착",u"찬",u"찮",u"찰",u"참",u"찹",u"찻",u"찼",u"창",u"찾",u"채",u"책",u"챈",u"챌",u"챔",u"챕",u"챗",u"챘",u"챙",u"챠",u"챤",u"챦",u"챨",u"챰",u"챵",u"처",u"척",u"천",u"철",u"첨",u"첩",u"첫",u"첬",u"청",u"체",u"첵",u"첸",u"첼",u"쳄",u"쳅",u"쳇",u"쳉",u"쳐",u"쳔",u"쳤",u"쳬",u"쳰",u"촁",u"초",u"촉",u"촌",u"촐",u"촘",u"촙",u"촛",u"총",u"촤",u"촨",u"촬",u"촹",u"최",u"쵠",u"쵤",u"쵬",u"쵭",u"쵯",u"쵱",u"쵸",u"춈",u"추",u"축",u"춘",u"출",u"춤",u"춥",u"춧",u"충",u"춰",u"췄",u"췌",u"췐",u"취",u"췬",u"췰",u"췸",u"췹",u"췻",u"췽",u"츄",u"츈",u"츌",u"츔",u"츙",u"츠",u"측",u"츤",u"츨",u"츰",u"츱",u"츳",u"층",u"치",u"칙",u"친",u"칟",u"칠",u"칡",u"침",u"칩",u"칫",u"칭",u"카",u"칵",u"칸",u"칼",u"캄",u"캅",u"캇",u"캉",u"캐",u"캑",u"캔",u"캘",u"캠",u"캡",u"캣",u"캤",u"캥",u"캬",u"캭",u"컁",u"커",u"컥",u"컨",u"컫",u"컬",u"컴",u"컵",u"컷",u"컸",u"컹",u"케",u"켁",u"켄",u"켈",u"켐",u"켑",u"켓",u"켕",u"켜",u"켠",u"켤",u"켬",u"켭",u"켯",u"켰",u"켱",u"켸",u"코",u"콕",u"콘",u"콜",u"콤",u"콥",u"콧",u"콩",u"콰",u"콱",u"콴",u"콸",u"쾀",u"쾅",u"쾌",u"쾡",u"쾨",u"쾰",u"쿄",u"쿠",u"쿡",u"쿤",u"쿨",u"쿰",u"쿱",u"쿳",u"쿵",u"쿼",u"퀀",u"퀄",u"퀑",u"퀘",u"퀭",u"퀴",u"퀵",u"퀸",u"퀼",u"큄",u"큅",u"큇",u"큉",u"큐",u"큔",u"큘",u"큠",u"크",u"큭",u"큰",u"클",u"큼",u"큽",u"킁",u"키",u"킥",u"킨",u"킬",u"킴",u"킵",u"킷",u"킹",u"타",u"탁",u"탄",u"탈",u"탉",u"탐",u"탑",u"탓",u"탔",u"탕",u"태",u"택",u"탠",u"탤",u"탬",u"탭",u"탯",u"탰",u"탱",u"탸",u"턍",u"터",u"턱",u"턴",u"털",u"턺",u"텀",u"텁",u"텃",u"텄",u"텅",u"테",u"텍",u"텐",u"텔",u"템",u"텝",u"텟",u"텡",u"텨",u"텬",u"텼",u"톄",u"톈",u"토",u"톡",u"톤",u"톨",u"톰",u"톱",u"톳",u"통",u"톺",u"톼",u"퇀",u"퇘",u"퇴",u"퇸",u"툇",u"툉",u"툐",u"투",u"툭",u"툰",u"툴",u"툼",u"툽",u"툿",u"퉁",u"퉈",u"퉜",u"퉤",u"튀",u"튁",u"튄",u"튈",u"튐",u"튑",u"튕",u"튜",u"튠",u"튤",u"튬",u"튱",u"트",u"특",u"튼",u"튿",u"틀",u"틂",u"틈",u"틉",u"틋",u"틔",u"틘",u"틜",u"틤",u"틥",u"티",u"틱",u"틴",u"틸",u"팀",u"팁",u"팃",u"팅",u"파",u"팍",u"팎",u"판",u"팔",u"팖",u"팜",u"팝",u"팟",u"팠",u"팡",u"팥",u"패",u"팩",u"팬",u"팰",u"팸",u"팹",u"팻",u"팼",u"팽",u"퍄",u"퍅",u"퍼",u"퍽",u"펀",u"펄",u"펌",u"펍",u"펏",u"펐",u"펑",u"페",u"펙",u"펜",u"펠",u"펨",u"펩",u"펫",u"펭",u"펴",u"편",u"펼",u"폄",u"폅",u"폈",u"평",u"폐",u"폘",u"폡",u"폣",u"포",u"폭",u"폰",u"폴",u"폼",u"폽",u"폿",u"퐁",u"퐈",u"퐝",u"푀",u"푄",u"표",u"푠",u"푤",u"푭",u"푯",u"푸",u"푹",u"푼",u"푿",u"풀",u"풂",u"품",u"풉",u"풋",u"풍",u"풔",u"풩",u"퓌",u"퓐",u"퓔",u"퓜",u"퓟",u"퓨",u"퓬",u"퓰",u"퓸",u"퓻",u"퓽",u"프",u"픈",u"플",u"픔",u"픕",u"픗",u"피",u"픽",u"핀",u"필",u"핌",u"핍",u"핏",u"핑",u"하",u"학",u"한",u"할",u"핥",u"함",u"합",u"핫",u"항",u"해",u"핵",u"핸",u"핼",u"햄",u"햅",u"햇",u"했",u"행",u"햐",u"향",u"허",u"헉",u"헌",u"헐",u"헒",u"험",u"헙",u"헛",u"헝",u"헤",u"헥",u"헨",u"헬",u"헴",u"헵",u"헷",u"헹",u"혀",u"혁",u"현",u"혈",u"혐",u"협",u"혓",u"혔",u"형",u"혜",u"혠",u"혤",u"혭",u"호",u"혹",u"혼",u"홀",u"홅",u"홈",u"홉",u"홋",u"홍",u"홑",u"화",u"확",u"환",u"활",u"홧",u"황",u"홰",u"홱",u"홴",u"횃",u"횅",u"회",u"획",u"횐",u"횔",u"횝",u"횟",u"횡",u"효",u"횬",u"횰",u"횹",u"횻",u"후",u"훅",u"훈",u"훌",u"훑",u"훔",u"훗",u"훙",u"훠",u"훤",u"훨",u"훰",u"훵",u"훼",u"훽",u"휀",u"휄",u"휑",u"휘",u"휙",u"휜",u"휠",u"휨",u"휩",u"휫",u"휭",u"휴",u"휵",u"휸",u"휼",u"흄",u"흇",u"흉",u"흐",u"흑",u"흔",u"흖",u"흗",u"흘",u"흙",u"흠",u"흡",u"흣",u"흥",u"흩",u"희",u"흰",u"흴",u"흼",u"흽",u"힁",u"히",u"힉",u"힌",u"힐",u"힘",u"힙",u"힛",u"힝"
]
ADOBE_KR9 = [
u"가",u"각",u"간",u"갇",u"갈",u"갉",u"갊",u"갋",u"감",u"갑",u"값",u"갓",u"갔",u"강",u"갖",u"갗",u"같",u"갚",u"갛",u"갸",u"갹",u"갼",u"걀",u"걋",u"걍",u"거",u"걱",u"건",u"걷",u"걸",u"걺",u"검",u"겁",u"겂",u"것",u"겄",u"겅",u"겆",u"겉",u"겊",u"겋",u"겨",u"격",u"겪",u"견",u"겯",u"결",u"겷",u"겸",u"겹",u"겻",u"겼",u"경",u"겿",u"곁",u"기",u"긱",u"긴",u"긷",u"길",u"긺",u"김",u"깁",u"깃",u"깄",u"깅",u"깆",u"깊",u"개",u"객",u"갠",u"갣",u"갤",u"갬",u"갭",u"갯",u"갰",u"갱",u"걔",u"걘",u"걜",u"걥",u"게",u"겍",u"겐",u"겔",u"겜",u"겝",u"겟",u"겠",u"겡",u"계",u"곈",u"곌",u"곕",u"곗",u"곘",u"고",u"곡",u"곤",u"곧",u"골",u"곪",u"곬",u"곯",u"곰",u"곱",u"곳",u"공",u"곶",u"곹",u"교",u"굔",u"굘",u"굠",u"굡",u"굣",u"굥",u"구",u"국",u"군",u"굳",u"굴",u"굵",u"굶",u"굻",u"굼",u"굽",u"굿",u"궁",u"궂",u"궃",u"규",u"균",u"귤",u"귬",u"귭",u"그",u"극",u"근",u"귿",u"글",u"긁",u"긂",u"긇",u"금",u"급",u"긋",u"긍",u"긏",u"긑",u"긓",u"과",u"곽",u"관",u"괄",u"괆",u"괌",u"괍",u"괏",u"괐",u"광",u"괒",u"괘",u"괜",u"괠",u"괢",u"괩",u"괬",u"괭",u"괴",u"괵",u"괸",u"괼",u"굄",u"굅",u"굇",u"굉",u"궈",u"궉",u"권",u"궐",u"궜",u"궝",u"궤",u"궷",u"궸",u"귀",u"귁",u"귄",u"귈",u"귐",u"귑",u"귓",u"귕",u"긔",u"긘",u"긩",u"까",u"깍",u"깎",u"깐",u"깔",u"깖",u"깜",u"깝",u"깟",u"깠",u"깡",u"깥",u"꺄",u"꺅",u"꺆",u"꺌",u"꺍",u"꺼",u"꺽",u"꺾",u"껀",u"껄",u"껌",u"껍",u"껏",u"껐",u"껑",u"껓",u"껕",u"껴",u"껸",u"껼",u"꼇",u"꼈",u"꼉",u"꼍",u"끼",u"끽",u"낀",u"낄",u"낌",u"낍",u"낏",u"낐",u"낑",u"깨",u"깩",u"깬",u"깯",u"깰",u"깸",u"깹",u"깻",u"깼",u"깽",u"꺠",u"꺤",u"께",u"껙",u"껜",u"껨",u"껫",u"껭",u"꼐",u"꼬",u"꼭",u"꼰",u"꼲",u"꼳",u"꼴",u"꼼",u"꼽",u"꼿",u"꽁",u"꽂",u"꽃",u"꽅",u"꾜",u"꾸",u"꾹",u"꾼",u"꿀",u"꿇",u"꿈",u"꿉",u"꿋",u"꿍",u"꿎",u"꿏",u"뀨",u"뀰",u"뀼",u"끄",u"끅",u"끈",u"끊",u"끌",u"끎",u"끓",u"끔",u"끕",u"끗",u"끙",u"끝",u"꽈",u"꽉",u"꽌",u"꽐",u"꽜",u"꽝",u"꽤",u"꽥",u"꽨",u"꽸",u"꽹",u"꾀",u"꾄",u"꾈",u"꾐",u"꾑",u"꾕",u"꿔",u"꿘",u"꿜",u"꿨",u"꿩",u"꿰",u"꿱",u"꿴",u"꿸",u"뀀",u"뀁",u"뀄",u"뀌",u"뀐",u"뀔",u"뀜",u"뀝",u"끠",u"끤",u"나",u"낙",u"낚",u"난",u"낟",u"날",u"낡",u"낢",u"남",u"납",u"낫",u"났",u"낭",u"낮",u"낯",u"낱",u"낳",u"냐",u"냑",u"냔",u"냗",u"냘",u"냠",u"냡",u"냣",u"냥",u"너",u"넉",u"넋",u"넌",u"넏",u"널",u"넑",u"넒",u"넓",u"넘",u"넙",u"넛",u"넜",u"넝",u"넢",u"넣",u"녀",u"녁",u"년",u"녇",u"녈",u"념",u"녑",u"녔",u"녕",u"녘",u"니",u"닉",u"닌",u"닏",u"닐",u"닒",u"님",u"닙",u"닛",u"닝",u"닞",u"닠",u"닢",u"내",u"낵",u"낸",u"낻",u"낼",u"냄",u"냅",u"냇",u"냈",u"냉",u"냬",u"네",u"넥",u"넨",u"넫",u"넬",u"넴",u"넵",u"넷",u"넸",u"넹",u"넾",u"녜",u"녠",u"녱",u"노",u"녹",u"논",u"놀",u"놁",u"놂",u"놈",u"놉",u"놋",u"농",u"놑",u"높",u"놓",u"뇨",u"뇩",u"뇬",u"뇰",u"뇸",u"뇹",u"뇻",u"뇽",u"누",u"눅",u"눈",u"눋",u"눌",u"눍",u"눔",u"눕",u"눗",u"눙",u"눝",u"뉴",u"뉵",u"뉻",u"뉼",u"늄",u"늅",u"늉",u"느",u"늑",u"는",u"늗",u"늘",u"늙",u"늚",u"늠",u"늡",u"늣",u"능",u"늦",u"늧",u"늪",u"늫",u"놔",u"놘",u"놜",u"놥",u"놨",u"놰",u"뇄",u"뇌",u"뇍",u"뇐",u"뇔",u"뇜",u"뇝",u"뇟",u"뇡",u"눠",u"눴",u"눼",u"뉘",u"뉜",u"뉠",u"뉨",u"뉩",u"늬",u"늰",u"늴",u"늼",u"늿",u"닁",u"다",u"닥",u"닦",u"단",u"닫",u"달",u"닭",u"닮",u"닯",u"닳",u"담",u"답",u"닷",u"닸",u"당",u"닺",u"닻",u"닽",u"닿",u"댜",u"댠",u"댱",u"더",u"덕",u"덖",u"던",u"덛",u"덜",u"덞",u"덟",u"덤",u"덥",u"덧",u"덩",u"덫",u"덮",u"덯",u"뎌",u"뎐",u"뎔",u"뎠",u"뎡",u"디",u"딕",u"딘",u"딛",u"딜",u"딤",u"딥",u"딧",u"딨",u"딩",u"딪",u"딫",u"딮",u"대",u"댁",u"댄",u"댈",u"댐",u"댑",u"댓",u"댔",u"댕",u"댖",u"데",u"덱",u"덴",u"델",u"뎀",u"뎁",u"뎃",u"뎄",u"뎅",u"뎨",u"뎬",u"도",u"독",u"돈",u"돋",u"돌",u"돎",u"돐",u"돔",u"돕",u"돗",u"동",u"돛",u"돝",u"됴",u"두",u"둑",u"둔",u"둗",u"둘",u"둚",u"둠",u"둡",u"둣",u"둥",u"듀",u"듄",u"듈",u"듐",u"듕",u"드",u"득",u"든",u"듣",u"들",u"듥",u"듦",u"듧",u"듬",u"듭",u"듯",u"등",u"돠",u"돤",u"돨",u"돼",u"됏",u"됐",u"되",u"된",u"될",u"됨",u"됩",u"됫",u"됬",u"됭",u"둬",u"뒀",u"뒈",u"뒙",u"뒝",u"뒤",u"뒨",u"뒬",u"뒵",u"뒷",u"뒸",u"뒹",u"듸",u"듼",u"딀",u"따",u"딱",u"딲",u"딴",u"딷",u"딸",u"땀",u"땁",u"땃",u"땄",u"땅",u"땋",u"떠",u"떡",u"떤",u"떨",u"떪",u"떫",u"떰",u"떱",u"떳",u"떴",u"떵",u"떻",u"뗘",u"뗬",u"띠",u"띡",u"띤",u"띨",u"띰",u"띱",u"띳",u"띵",u"때",u"땍",u"땐",u"땔",u"땜",u"땝",u"땟",u"땠",u"땡",u"떄",u"떈",u"떔",u"떙",u"떼",u"떽",u"뗀",u"뗄",u"뗌",u"뗍",u"뗏",u"뗐",u"뗑",u"또",u"똑",u"똔",u"똘",u"똠",u"똡",u"똣",u"똥",u"뚜",u"뚝",u"뚠",u"뚤",u"뚧",u"뚫",u"뚬",u"뚯",u"뚱",u"뜌",u"뜨",u"뜩",u"뜬",u"뜯",u"뜰",u"뜳",u"뜸",u"뜹",u"뜻",u"뜽",u"뜾",u"띃",u"똬",u"똭",u"똰",u"똴",u"뙇",u"뙈",u"뙜",u"뙤",u"뙨",u"뚸",u"뛔",u"뛰",u"뛴",u"뛸",u"뜀",u"뜁",u"뜄",u"뜅",u"띄",u"띈",u"띌",u"띔",u"띕",u"라",u"락",u"란",u"랃",u"랄",u"람",u"랍",u"랏",u"랐",u"랑",u"랒",u"랖",u"랗",u"랴",u"략",u"랸",u"럅",u"럇",u"량",u"러",u"럭",u"런",u"럲",u"럳",u"럴",u"럼",u"럽",u"럿",u"렀",u"렁",u"렇",u"려",u"력",u"련",u"렫",u"렬",u"렴",u"렵",u"렷",u"렸",u"령",u"리",u"릭",u"린",u"릴",u"림",u"립",u"릿",u"맀",u"링",u"맆",u"래",u"랙",u"랜",u"랟",u"랠",u"램",u"랩",u"랫",u"랬",u"랭",u"랰",u"랲",u"럐",u"럔",u"레",u"렉",u"렌",u"렐",u"렘",u"렙",u"렛",u"렜",u"렝",u"례",u"롄",u"롑",u"롓",u"로",u"록",u"론",u"롣",u"롤",u"롬",u"롭",u"롯",u"롱",u"료",u"룐",u"룔",u"룝",u"룟",u"룡",u"루",u"룩",u"룬",u"룰",u"룸",u"룹",u"룻",u"룽",u"류",u"륙",u"륜",u"률",u"륨",u"륩",u"륫",u"륭",u"르",u"륵",u"른",u"를",u"름",u"릅",u"릇",u"릉",u"릊",u"릍",u"릎",u"릏",u"롸",u"롹",u"롼",u"뢍",u"뢔",u"뢨",u"뢰",u"뢴",u"뢸",u"룀",u"룁",u"룃",u"룅",u"뤄",u"뤈",u"뤘",u"뤠",u"뤤",u"뤼",u"뤽",u"륀",u"륄",u"륌",u"륏",u"륑",u"릐",u"릔",u"마",u"막",u"만",u"많",u"맏",u"말",u"맑",u"맒",u"맔",u"맘",u"맙",u"맛",u"맜",u"망",u"맞",u"맟",u"맡",u"맢",u"맣",u"먀",u"먁",u"먄",u"먈",u"먐",u"먕",u"머",u"먹",u"먼",u"멀",u"멂",u"멈",u"멉",u"멋",u"멌",u"멍",u"멎",u"멓",u"며",u"멱",u"면",u"멷",u"멸",u"몃",u"몄",u"명",u"몇",u"미",u"믹",u"민",u"믿",u"밀",u"밂",u"밈",u"밉",u"밋",u"밌",u"밍",u"및",u"밑",u"매",u"맥",u"맨",u"맫",u"맬",u"맴",u"맵",u"맷",u"맸",u"맹",u"맺",u"맻",u"맽",u"메",u"멕",u"멘",u"멛",u"멜",u"멤",u"멥",u"멧",u"멨",u"멩",u"멫",u"몌",u"몐",u"모",u"목",u"몫",u"몬",u"몯",u"몰",u"몱",u"몲",u"몸",u"몹",u"못",u"몽",u"묘",u"묜",u"묠",u"묩",u"묫",u"무",u"묵",u"묶",u"문",u"묻",u"물",u"묽",u"묾",u"뭄",u"뭅",u"뭇",u"뭉",u"뭍",u"뭏",u"뮤",u"뮨",u"뮬",u"뮴",u"뮷",u"뮹",u"므",u"믁",u"믄",u"믈",u"믐",u"믑",u"믓",u"믕",u"뫄",u"뫈",u"뫘",u"뫙",u"뫠",u"뫴",u"뫼",u"묀",u"묄",u"묌",u"묍",u"묏",u"묑",u"뭐",u"뭔",u"뭘",u"뭡",u"뭣",u"뭤",u"뭥",u"뭬",u"뮈",u"뮊",u"뮌",u"뮐",u"뮙",u"뮛",u"믜",u"믠",u"믭",u"믱",u"바",u"박",u"밖",u"밗",u"반",u"받",u"발",u"밝",u"밞",u"밟",u"밣",u"밤",u"밥",u"밧",u"밨",u"방",u"밫",u"밭",u"뱌",u"뱍",u"뱐",u"뱜",u"뱝",u"뱟",u"뱡",u"버",u"벅",u"번",u"벋",u"벌",u"벎",u"범",u"법",u"벗",u"벘",u"벙",u"벚",u"벝",u"벟",u"벼",u"벽",u"변",u"별",u"볌",u"볍",u"볏",u"볐",u"병",u"볓",u"비",u"빅",u"빈",u"빋",u"빌",u"빎",u"빔",u"빕",u"빗",u"빘",u"빙",u"빚",u"빛",u"배",u"백",u"밲",u"밴",u"밷",u"밸",u"뱀",u"뱁",u"뱃",u"뱄",u"뱅",u"뱉",u"베",u"벡",u"벤",u"벧",u"벨",u"벰",u"벱",u"벳",u"벴",u"벵",u"볕",u"볘",u"볜",u"보",u"복",u"볶",u"본",u"볻",u"볼",u"볽",u"볾",u"볿",u"봄",u"봅",u"봇",u"봉",u"뵤",u"뵨",u"뵴",u"부",u"북",u"분",u"붇",u"불",u"붉",u"붊",u"붐",u"붑",u"붓",u"붔",u"붕",u"붙",u"붚",u"뷰",u"뷴",u"뷸",u"븀",u"븁",u"븃",u"븅",u"브",u"븍",u"븐",u"블",u"븕",u"븜",u"븝",u"븟",u"븡",u"봐",u"봔",u"봣",u"봤",u"봥",u"봬",u"뵀",u"뵈",u"뵉",u"뵌",u"뵐",u"뵘",u"뵙",u"뵜",u"붜",u"붝",u"붠",u"붤",u"붭",u"붰",u"붴",u"붸",u"뷁",u"뷔",u"뷕",u"뷘",u"뷜",u"뷥",u"뷩",u"븨",u"븩",u"븰",u"븽",u"빠",u"빡",u"빤",u"빧",u"빨",u"빩",u"빪",u"빰",u"빱",u"빳",u"빴",u"빵",u"빻",u"뺘",u"뺙",u"뺜",u"뺨",u"뻐",u"뻑",u"뻔",u"뻗",u"뻘",u"뻙",u"뻠",u"뻣",u"뻤",u"뻥",u"뼈",u"뼉",u"뼌",u"뼘",u"뼙",u"뼛",u"뼜",u"뼝",u"삐",u"삑",u"삔",u"삘",u"삠",u"삡",u"삣",u"삥",u"빼",u"빽",u"빾",u"뺀",u"뺄",u"뺌",u"뺍",u"뺏",u"뺐",u"뺑",u"뻬",u"뻰",u"뼁",u"뽀",u"뽁",u"뽄",u"뽈",u"뽐",u"뽑",u"뽓",u"뽕",u"뾰",u"뾱",u"뿅",u"뿌",u"뿍",u"뿐",u"뿔",u"뿕",u"뿜",u"뿝",u"뿟",u"뿡",u"쀼",u"쁑",u"쁘",u"쁜",u"쁠",u"쁨",u"쁩",u"쁭",u"뾔",u"쀠",u"사",u"삭",u"삯",u"산",u"삳",u"살",u"삵",u"삶",u"삼",u"삽",u"삿",u"샀",u"상",u"샅",u"샆",u"샤",u"샥",u"샨",u"샬",u"샴",u"샵",u"샷",u"샹",u"샾",u"서",u"석",u"섞",u"섟",u"선",u"섣",u"설",u"섦",u"섧",u"섬",u"섭",u"섯",u"섰",u"성",u"섶",u"셔",u"셕",u"션",u"셜",u"셤",u"셥",u"셧",u"셨",u"셩",u"시",u"식",u"신",u"싣",u"실",u"싥",u"싫",u"심",u"십",u"싯",u"싰",u"싱",u"싳",u"싶",u"새",u"색",u"샌",u"샏",u"샐",u"샘",u"샙",u"샛",u"샜",u"생",u"섀",u"섁",u"섄",u"섈",u"섐",u"섕",u"세",u"섹",u"센",u"섿",u"셀",u"셈",u"셉",u"셋",u"셌",u"셍",u"셑",u"셰",u"셱",u"셴",u"셸",u"솀",u"솁",u"솅",u"소",u"속",u"솎",u"손",u"솓",u"솔",u"솖",u"솜",u"솝",u"솟",u"송",u"솥",u"쇼",u"쇽",u"숀",u"숄",u"숌",u"숍",u"숏",u"숑",u"숖",u"수",u"숙",u"순",u"숟",u"술",u"숨",u"숩",u"숫",u"숭",u"숯",u"숱",u"숲",u"슈",u"슉",u"슌",u"슐",u"슘",u"슛",u"슝",u"스",u"슥",u"슨",u"슫",u"슬",u"슭",u"슲",u"슴",u"습",u"슷",u"승",u"솨",u"솩",u"솬",u"솰",u"솽",u"쇄",u"쇈",u"쇌",u"쇔",u"쇗",u"쇘",u"쇠",u"쇤",u"쇨",u"쇰",u"쇱",u"쇳",u"쇴",u"쇵",u"숴",u"쉈",u"쉐",u"쉑",u"쉔",u"쉘",u"쉠",u"쉥",u"쉬",u"쉭",u"쉰",u"쉴",u"쉼",u"쉽",u"쉿",u"슁",u"싀",u"싁",u"싸",u"싹",u"싻",u"싼",u"싿",u"쌀",u"쌈",u"쌉",u"쌌",u"쌍",u"쌓",u"써",u"썩",u"썬",u"썰",u"썲",u"썸",u"썹",u"썼",u"썽",u"쎂",u"쎠",u"쎤",u"쎵",u"씨",u"씩",u"씫",u"씬",u"씰",u"씸",u"씹",u"씻",u"씼",u"씽",u"씿",u"쌔",u"쌕",u"쌘",u"쌜",u"쌤",u"쌥",u"쌨",u"쌩",u"쌰",u"쌱",u"썅",u"쎄",u"쎅",u"쎈",u"쎌",u"쎔",u"쎼",u"쏀",u"쏘",u"쏙",u"쏚",u"쏜",u"쏟",u"쏠",u"쏢",u"쏨",u"쏩",u"쏭",u"쑈",u"쑝",u"쑤",u"쑥",u"쑨",u"쑬",u"쑴",u"쑵",u"쑹",u"쓔",u"쓩",u"쓰",u"쓱",u"쓴",u"쓸",u"쓺",u"쓿",u"씀",u"씁",u"씃",u"쏴",u"쏵",u"쏸",u"쏼",u"쐈",u"쐋",u"쐐",u"쐤",u"쐬",u"쐰",u"쐴",u"쐼",u"쐽",u"쑀",u"쒀",u"쒐",u"쒔",u"쒜",u"쒠",u"쒬",u"쒸",u"쒼",u"씌",u"씐",u"씔",u"씜",u"아",u"악",u"안",u"앉",u"않",u"앋",u"알",u"앍",u"앎",u"앏",u"앓",u"암",u"압",u"앗",u"았",u"앙",u"앜",u"앝",u"앞",u"야",u"약",u"얀",u"얄",u"얇",u"얌",u"얍",u"얏",u"얐",u"양",u"얕",u"얗",u"어",u"억",u"언",u"얹",u"얺",u"얻",u"얼",u"얽",u"얾",u"엄",u"업",u"없",u"엇",u"었",u"엉",u"엊",u"엌",u"엎",u"엏",u"여",u"역",u"엮",u"연",u"열",u"엶",u"엷",u"염",u"엽",u"엾",u"엿",u"였",u"영",u"옅",u"옆",u"옇",u"이",u"익",u"인",u"읻",u"일",u"읽",u"읾",u"잃",u"임",u"입",u"잇",u"있",u"잉",u"잊",u"잌",u"잍",u"잎",u"애",u"액",u"앤",u"앨",u"앰",u"앱",u"앳",u"앴",u"앵",u"얘",u"얜",u"얠",u"얩",u"얬",u"얭",u"에",u"엑",u"엔",u"엘",u"엠",u"엡",u"엣",u"엤",u"엥",u"예",u"옌",u"옏",u"옐",u"옘",u"옙",u"옛",u"옜",u"옝",u"오",u"옥",u"옦",u"온",u"옫",u"올",u"옭",u"옮",u"옯",u"옰",u"옳",u"옴",u"옵",u"옷",u"옹",u"옻",u"요",u"욕",u"욘",u"욜",u"욤",u"욥",u"욧",u"용",u"우",u"욱",u"운",u"욷",u"울",u"욹",u"욺",u"움",u"웁",u"웂",u"웃",u"웅",u"웇",u"유",u"육",u"윤",u"율",u"윰",u"윱",u"윳",u"융",u"윷",u"으",u"윽",u"윾",u"은",u"읃",u"을",u"읇",u"읊",u"음",u"읍",u"읎",u"읏",u"응",u"읒",u"읓",u"읔",u"읕",u"읖",u"읗",u"와",u"왁",u"완",u"왈",u"왎",u"왐",u"왑",u"왓",u"왔",u"왕",u"왘",u"왜",u"왝",u"왠",u"왬",u"왭",u"왯",u"왰",u"왱",u"외",u"왹",u"왼",u"욀",u"욈",u"욉",u"욋",u"욌",u"욍",u"워",u"웍",u"원",u"월",u"웜",u"웝",u"웟",u"웠",u"웡",u"웨",u"웩",u"웬",u"웰",u"웸",u"웹",u"웻",u"웽",u"위",u"윅",u"윈",u"윌",u"윔",u"윕",u"윗",u"윘",u"윙",u"의",u"읜",u"읠",u"읨",u"읩",u"읫",u"읬",u"읭",u"자",u"작",u"잔",u"잖",u"잗",u"잘",u"잚",u"잠",u"잡",u"잣",u"잤",u"장",u"잦",u"쟈",u"쟉",u"쟌",u"쟎",u"쟐",u"쟘",u"쟝",u"저",u"적",u"젂",u"전",u"젇",u"절",u"젉",u"젊",u"젋",u"점",u"접",u"젓",u"젔",u"정",u"젖",u"져",u"젹",u"젼",u"졀",u"졂",u"졈",u"졉",u"졋",u"졌",u"졍",u"지",u"직",u"진",u"짇",u"질",u"짊",u"짐",u"집",u"짓",u"짔",u"징",u"짖",u"짗",u"짙",u"짚",u"재",u"잭",u"잰",u"잴",u"잼",u"잽",u"잿",u"쟀",u"쟁",u"쟤",u"쟨",u"쟬",u"쟵",u"제",u"젝",u"젠",u"젤",u"젬",u"젭",u"젯",u"젱",u"졔",u"조",u"족",u"존",u"졸",u"졺",u"좀",u"좁",u"좃",u"종",u"좆",u"좇",u"좋",u"죠",u"죡",u"죤",u"죵",u"주",u"죽",u"준",u"줄",u"줅",u"줆",u"줌",u"줍",u"줏",u"중",u"쥬",u"쥭",u"쥰",u"쥴",u"쥼",u"즁",u"즈",u"즉",u"즌",u"즐",u"즒",u"즘",u"즙",u"즛",u"증",u"좌",u"좍",u"좐",u"좔",u"좝",u"좟",u"좡",u"좦",u"좨",u"좬",u"좼",u"좽",u"죄",u"죅",u"죈",u"죌",u"죔",u"죕",u"죗",u"죙",u"줘",u"줬",u"줴",u"쥐",u"쥑",u"쥔",u"쥘",u"쥠",u"쥡",u"쥣",u"즤",u"짜",u"짝",u"짠",u"짢",u"짣",u"짤",u"짧",u"짬",u"짭",u"짯",u"짰",u"짱",u"짲",u"쨔",u"쨘",u"쨤",u"쨩",u"쩌",u"쩍",u"쩐",u"쩔",u"쩜",u"쩝",u"쩟",u"쩠",u"쩡",u"쪄",u"쪘",u"찌",u"찍",u"찐",u"찓",u"찔",u"찜",u"찝",u"찟",u"찡",u"찢",u"찦",u"찧",u"째",u"짹",u"짼",u"쨀",u"쨈",u"쨉",u"쨋",u"쨌",u"쨍",u"쨰",u"쩨",u"쩰",u"쩽",u"쪼",u"쪽",u"쫀",u"쫃",u"쫄",u"쫌",u"쫍",u"쫏",u"쫑",u"쫒",u"쫓",u"쬬",u"쬭",u"쬲",u"쭁",u"쭈",u"쭉",u"쭌",u"쭐",u"쭘",u"쭙",u"쭛",u"쭝",u"쮸",u"쯍",u"쯔",u"쯕",u"쯤",u"쯧",u"쯩",u"쫘",u"쫙",u"쫜",u"쫠",u"쫬",u"쫴",u"쬈",u"쬐",u"쬔",u"쬘",u"쬠",u"쬡",u"쬧",u"쭤",u"쭸",u"쭹",u"쮀",u"쮓",u"쮜",u"차",u"착",u"찬",u"찮",u"찰",u"참",u"찹",u"찻",u"찼",u"창",u"찾",u"찿",u"챠",u"챤",u"챦",u"챨",u"챰",u"챵",u"처",u"척",u"천",u"철",u"첨",u"첩",u"첫",u"첬",u"청",u"쳐",u"쳔",u"쳡",u"쳤",u"쳥",u"치",u"칙",u"친",u"칟",u"칠",u"칡",u"칢",u"침",u"칩",u"칫",u"칬",u"칭",u"칮",u"칰",u"채",u"책",u"챈",u"챌",u"챔",u"챕",u"챗",u"챘",u"챙",u"체",u"첵",u"첸",u"첼",u"쳄",u"쳅",u"쳇",u"쳉",u"쳊",u"쳬",u"쳰",u"촁",u"초",u"촉",u"촌",u"촐",u"촘",u"촙",u"촛",u"총",u"촣",u"쵸",u"춈",u"추",u"축",u"춘",u"출",u"춤",u"춥",u"춧",u"충",u"츄",u"츅",u"츈",u"츌",u"츔",u"츙",u"츠",u"측",u"츤",u"츨",u"츩",u"츰",u"츱",u"츳",u"층",u"촤",u"촥",u"촨",u"촬",u"촵",u"촹",u"쵀",u"최",u"쵠",u"쵤",u"쵬",u"쵭",u"쵯",u"쵱",u"춰",u"췄",u"췌",u"췍",u"췐",u"췔",u"취",u"췬",u"췰",u"췸",u"췹",u"췻",u"췽",u"츼",u"카",u"칵",u"칸",u"칻",u"칼",u"캄",u"캅",u"캇",u"캉",u"캬",u"캭",u"캰",u"컁",u"컄",u"커",u"컥",u"컨",u"컫",u"컬",u"컴",u"컵",u"컷",u"컸",u"컹",u"컽",u"켜",u"켠",u"켤",u"켬",u"켭",u"켯",u"켰",u"켱",u"키",u"킥",u"킨",u"킬",u"킴",u"킵",u"킷",u"킸",u"킹",u"캐",u"캑",u"캔",u"캘",u"캠",u"캡",u"캣",u"캤",u"캥",u"캨",u"케",u"켁",u"켄",u"켈",u"켐",u"켑",u"켓",u"켔",u"켕",u"켘",u"켙",u"켸",u"코",u"콕",u"콘",u"콛",u"콜",u"콤",u"콥",u"콧",u"콩",u"쿄",u"쿈",u"쿠",u"쿡",u"쿤",u"쿨",u"쿰",u"쿱",u"쿳",u"쿵",u"큐",u"큔",u"큘",u"큠",u"크",u"큭",u"큰",u"큲",u"클",u"큼",u"큽",u"킁",u"킄",u"콰",u"콱",u"콴",u"콸",u"쾀",u"쾃",u"쾅",u"쾌",u"쾡",u"쾨",u"쾰",u"쿼",u"쿽",u"퀀",u"퀄",u"퀌",u"퀑",u"퀘",u"퀜",u"퀠",u"퀭",u"퀴",u"퀵",u"퀸",u"퀼",u"큄",u"큅",u"큇",u"큉",u"킈",u"타",u"탁",u"탄",u"탇",u"탈",u"탉",u"탐",u"탑",u"탓",u"탔",u"탕",u"터",u"턱",u"턴",u"털",u"턺",u"턻",u"텀",u"텁",u"텃",u"텄",u"텅",u"텨",u"텬",u"텰",u"텻",u"텼",u"티",u"틱",u"틴",u"틸",u"팀",u"팁",u"팃",u"팅",u"태",u"택",u"탠",u"탤",u"탬",u"탭",u"탯",u"탰",u"탱",u"탸",u"턍",u"턔",u"테",u"텍",u"텐",u"텔",u"템",u"텝",u"텟",u"텡",u"텦",u"톄",u"톈",u"토",u"톡",u"톤",u"톧",u"톨",u"톰",u"톱",u"톳",u"통",u"톺",u"툐",u"툥",u"투",u"툭",u"툰",u"툴",u"툶",u"툼",u"툽",u"툿",u"퉁",u"튜",u"튠",u"튤",u"튬",u"튱",u"트",u"특",u"튼",u"튿",u"틀",u"틂",u"틈",u"틉",u"틋",u"틍",u"틑",u"톼",u"퇀",u"퇘",u"퇴",u"퇸",u"퇻",u"툇",u"툉",u"퉈",u"퉜",u"퉤",u"퉷",u"튀",u"튁",u"튄",u"튈",u"튐",u"튑",u"튕",u"틔",u"틘",u"틜",u"틤",u"틥",u"파",u"팍",u"팎",u"판",u"팑",u"팓",u"팔",u"팖",u"팜",u"팝",u"팟",u"팠",u"팡",u"팤",u"팥",u"퍄",u"퍅",u"퍝",u"퍼",u"퍽",u"펀",u"펄",u"펌",u"펍",u"펏",u"펐",u"펑",u"펖",u"펴",u"펵",u"편",u"펼",u"폄",u"폅",u"폈",u"평",u"피",u"픽",u"핀",u"필",u"핌",u"핍",u"핏",u"핐",u"핑",u"패",u"팩",u"팬",u"팯",u"팰",u"팸",u"팹",u"팻",u"팼",u"팽",u"페",u"펙",u"펜",u"펠",u"펨",u"펩",u"펫",u"펭",u"폐",u"폔",u"폘",u"폡",u"폣",u"포",u"폭",u"폰",u"폴",u"폼",u"폽",u"폿",u"퐁",u"퐅",u"표",u"푠",u"푤",u"푭",u"푯",u"푸",u"푹",u"푼",u"푿",u"풀",u"풂",u"품",u"풉",u"풋",u"풍",u"퓨",u"퓬",u"퓰",u"퓸",u"퓻",u"퓽",u"프",u"픈",u"플",u"픔",u"픕",u"픗",u"픙",u"퐈",u"퐉",u"퐝",u"푀",u"푄",u"풔",u"풩",u"퓌",u"퓐",u"퓔",u"퓜",u"퓟",u"픠",u"픵",u"하",u"학",u"한",u"할",u"핤",u"핥",u"함",u"합",u"핫",u"항",u"핰",u"핳",u"햐",u"햔",u"햣",u"향",u"허",u"헉",u"헌",u"헐",u"헒",u"헗",u"험",u"헙",u"헛",u"헝",u"헠",u"헡",u"헣",u"혀",u"혁",u"현",u"혈",u"혐",u"협",u"혓",u"혔",u"형",u"히",u"힉",u"힌",u"힐",u"힘",u"힙",u"힛",u"힜",u"힝",u"힣",u"해",u"핵",u"핸",u"핻",u"핼",u"햄",u"햅",u"햇",u"했",u"행",u"햋",u"햏",u"햬",u"헀",u"헤",u"헥",u"헨",u"헬",u"헴",u"헵",u"헷",u"헸",u"헹",u"헿",u"혜",u"혠",u"혤",u"혭",u"호",u"혹",u"혼",u"홀",u"홅",u"홈",u"홉",u"홋",u"홍",u"홑",u"효",u"횬",u"횰",u"횹",u"횻",u"횽",u"후",u"훅",u"훈",u"훌",u"훍",u"훐",u"훑",u"훓",u"훔",u"훕",u"훗",u"훙",u"휴",u"휵",u"휸",u"휼",u"흄",u"흇",u"흉",u"흐",u"흑",u"흔",u"흖",u"흗",u"흘",u"흙",u"흝",u"흠",u"흡",u"흣",u"흥",u"흩",u"화",u"확",u"환",u"활",u"홥",u"홧",u"홨",u"황",u"홰",u"홱",u"홴",u"횃",u"횅",u"회",u"획",u"횐",u"횔",u"횝",u"횟",u"횡",u"훠",u"훤",u"훨",u"훰",u"훵",u"훼",u"훽",u"휀",u"휄",u"휑",u"휘",u"휙",u"휜",u"휠",u"휨",u"휩",u"휫",u"휭",u"희",u"흰",u"흴",u"흼",u"흽",u"힁"
]

CHAR_RANGE_LIST = [ADOBE_KR9, KSX_1001]
CHAR_RANGE_DICT= [{string : string for string in ADOBE_KR9}, {string : string for string in KSX_1001}]

try:
    JAMO_GROUP_DICT = flP.packageLib["com.Minwoo.GenerateHangeulComposition"]
except KeyError :
    NEW_JAMO_DICT = {**flP.packageLib, "com.Minwoo.GenerateHangeulComposition": {x:[] for x in JAMO_LABEL_EN}}
    flP.packageLib = NEW_JAMO_DICT
    JAMO_GROUP_DICT = flP.packageLib["com.Minwoo.GenerateHangeulComposition"]

################################################################################
# Hangeul Compositing Functions
################################################################################

def compose(chosung, jungsung, jongsung=u''):
    """This function returns a Hangul letter by composing the specified chosung, jungsung, and jongsung.
    @param chosung
    @param jungsung
    @param jongsung the terminal Hangul letter. This is optional if you do not need a jongsung."""

    if jongsung == None or jongsung == u'·' : jongsung = u''

    try:
        chosung_index = CHO.index(chosung)
        jungsung_index = JUNG.index(jungsung)
        jongsung_index = JONG.index(jongsung)
    except Exception:
        raise NotHangulException('No valid Hangul character index')

    composed = chr(0xAC00 + chosung_index * NUM_JUNG * NUM_JONG + jungsung_index * NUM_JONG + jongsung_index)
    try:
        if CHAR_RANGE == 2 :
            return composed 
        elif CHAR_RANGE ==3 :
            return composed if composed not in CHAR_RANGE_DICT[0] else False
        else :
            return CHAR_RANGE_DICT[CHAR_RANGE][composed] 
    except: 
        return False

def decompose(hangul_letter):
    """This function returns letters by decomposing the specified Hangul letter."""
    
    if len(hangul_letter) < 1:
        raise NotLetterException('')
    elif not is_hangul(hangul_letter):
        raise NotHangulException('')
    
    code = ord(hangul_letter) - FIRST_HANGUL_UNICODE
    jongsung_index = code % NUM_JONG
    code //= NUM_JONG
    jungsung_index = code % NUM_JUNG
    code //= NUM_JUNG
    chosung_index = code
    return (CHO[chosung_index], JUNG[jungsung_index], JONG[jongsung_index])

def is_jamo(letter):
    if letter in JAMO: 
        return letter
    else: return ''

def is_cho(charArr):
    for i in range(len(charArr)):
        if charArr[i] in CHO: 
            continue
        else:
            charArr[i] = u''
    return charArr

def is_jung(charArr):
    for i in range(len(charArr)):
        if charArr[i] in JUNG: 
            continue
        else:
            charArr[i] = u''
    return charArr

def is_jong(charArr):
    for i in range(len(charArr)):
        if charArr[i] in JONG: 
            continue
        elif charArr[i] == u'·':
            charArr[i] = u''
        else:
            return ''
    return charArr

def is_hangul(phrase):
    """Check whether the phrase is Hangul.
    This method ignores white spaces, punctuations, and numbers.
    @param phrase a target string
    @return True if the phrase is Hangul. False otherwise."""
    
    # If the input is only one character, test whether the character is Hangul.
    if len(phrase) == 1: return is_all_hangul(phrase)
    
    # Remove all white spaces, punctuations, numbers.
    exclude = set(string.whitespace + string.punctuation + '0123456789')
    phrase = ''.join(ch for ch in phrase if ch not in exclude)
    
    return is_all_hangul(phrase)

def is_all_hangul(phrase):
    """Check whether the phrase contains all Hangul letters
    @param phrase a target string
    @return True if the phrase only consists of Hangul. False otherwise."""
    
    for unicode_value in map(lambda letter:ord(letter), phrase):
        if unicode_value < FIRST_HANGUL_UNICODE or unicode_value > LAST_HANGUL_UNICODE:
            # Check whether the letter is chosungs, jungsungs, or jongsungs.
            if unicode_value not in map(lambda v: ord(v), CHO + JUNG + JONG[1:]):
                return False
    return True

def composeAllCases(chosung = [u''], jungsung = [u''], jongsung = [u''], jung_by_type = False, line_break = False):
    # if CHAR_RANGE == 0 : print('CHAR RANGE : KS X 1001 - 2350자')
    # if CHAR_RANGE == 1 : print('CHAR RANGE : ADOBE-KR-9 - 2780자')
    # if CHAR_RANGE == 2 : print('CHAR RANGE : 현대 한글 11172자')

    # if SORT_ORDER == 0 : print('SORT ORDER : 초성 순')
    # if SORT_ORDER == 1 : print('SORT ORDER : 중성 순')
    # if SORT_ORDER == 2 : print('SORT ORDER : 중성 모임꼴 순')
    # if SORT_ORDER == 3 : print('SORT ORDER : 종성 순')

    # print('초성: %s, 중성: %s, 종성: %s' %(''.join(chosung), ''.join(jungsung), ''.join(jongsung)))
    chosung = list(CHO) if is_cho(chosung)==[] else is_cho(chosung)
    chosung.sort()

    jungsung = list(JUNG) if is_jung(jungsung)==[] else is_jung(jungsung)
    if jung_by_type : 
        jungsung.sort(key=lambda x : JUNG_BY_TYPE.index(x))
    else: 
        jungsung.sort()

    jongsung = list(JONG) if is_jong(jongsung)==[] else is_jong(jongsung)
    jongsung.sort()

    composedChrList = []
    if SORT_ORDER == 0:
        for cho in chosung :
            for jung in jungsung:
                for jong in jongsung:
                    letter = compose(cho, jung, jong) 
                    if not letter : 
                        continue
                    composedChrList.append(letter)
                if line_break: 
                    if len(composedChrList)>0 and composedChrList[-1] != '\n' :
                        composedChrList.append('\n')
                    else: continue
    if SORT_ORDER == 1 :
        for jung in jungsung:
            for cho in chosung :
                for jong in jongsung:
                    letter = compose(cho, jung, jong) 
                    if not letter : 
                        continue
                    composedChrList.append(letter)
            if line_break: 
                if len(composedChrList)>0 and composedChrList[-1] != '\n' :
                    composedChrList.append('\n')
                else: continue
    if SORT_ORDER == 2:
        for jong in jongsung:
            for cho in chosung :
                for jung in jungsung:
                    letter = compose(cho, jung, jong) 
                    if not letter : 
                        continue
                    composedChrList.append(letter)
                    if line_break:
                        if len(composedChrList)>0 and composedChrList[-1] != '\n' :
                            composedChrList.append('\n')
                        else: continue

    # print(''.join(composedChrList))
    return composedChrList

################################################################################
# FL Interface
################################################################################

def setTextblock(charArr):
    symbolLists = fl6.fgSymbolList([fl6.fgSymbol(ord(chr)) for chr in charArr])   
    fl6.flItems().requestContent(symbolLists, 0)

def editOnCanvas(charArr, onNewTab=True):
    if onNewTab:
        legacy.fl.EditGlyph()
    setTextblock(charArr)

def copy2clip(str):
    cb = qapp.clipboard()
    cb.clear()
    cb.setText(str)  

################################################################################
# Widget
################################################################################

styleSheet = '''
QWidget{
    font-family: Malgun Gothic, Arial, sans-serif;
    font-size: 15px;
    font-weight: 400;
}
QPushButton:checked  {
    background-color: #3585fd;
    color: white;
    border: none;
    border-radius: 5px;
}
QPushButton:pressed  {
    background-color: #2d77e2;
    color: white;
    border-radius: 5px;
    border-none;
}
QPushButton {
    height: 25px;
}
QGroupBox {
}
'''

class ListWidget(QtGui.QListWidget):
    def __init__(self, aux, jamoIdx) -> None:
        super(ListWidget, self).__init__()
        self.aux = aux        
        self.setAlternatingRowColors(True)
        self.itemChanged.connect(self.itemNameChanged)

    def addCompItems(self):
        self.comps = self.aux.selected_jamo
        item = QtGui.QListWidgetItem()
        item.setData(256, self.comps)
        item.setText(','.join(self.comps))
        item.setFlags(1|2|16|32) # ItemIsSelectable | ItemIsEditable | ItemIsEnabled
        # print(320, item.data(256)) # UserRole
        self.addItem(item)
        self.aux.unselectAllJamo()
        self.aux.writeJamoGroups()

    def modifyCompItems(self):
        self.comps = self.aux.selected_jamo
        if self.comps != [] :
            item = self.currentItem()
            item.setData(256, self.comps)
            self.editItem(item)
            # print(item, self.comps)
        else: 
            QtGui.QMessageBox.information(self, "알림", "선택된 자소 그룹이 없습니다.")
        self.aux.writeJamoGroups()

    def removeCompItems(self):
        if self.currentItem():
            item = self.currentItem()
            row = self.currentRow
            self.takeItem(row)
        self.aux.writeJamoGroups()

    def itemNameChanged(self):
        self.aux.writeJamoGroups()
        
    def syncListSelectiontoBtn(self):
        try:
            self.aux.selected_jamo = list(self.currentItem().data(256))
        except AttributeError:
            self.aux.selected_jamo = []
        self.aux.updateBtnSelection()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.indexAt(event.pos()).isValid():
            # print(self.indexAt(event.pos()).data(256))
            curRow = self.indexAt(event.pos()).row()
            self.setCurrentRow(curRow)
            self.syncListSelectiontoBtn()
            # print(372, self.aux.selected_jamo)
        elif not self.currentRow == -1:
            # print(374, self.currentRow)
            self.clearSelection()
            self.aux.updateBtnSelection()
            self.setCurrentItem(None)
            self.syncListSelectiontoBtn()
            # print(379, self.aux.selected_jamo)
        else:
            self.clearSelection()
            # print(382, self.aux.selected_jamo)


    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.indexAt(event.pos()).isValid():
            curRow = self.indexAt(event.pos()).row()
            self.setCurrentRow(curRow)
            self.editItem(self.item(curRow))
            

class JamoWidget(QtGui.QWidget):
    def __init__(self, jamoIdx) :
        super(JamoWidget, self).__init__()
        self.jamoIdx = jamoIdx
        self.selected_jamo = []
        self.setStyleSheet(styleSheet)

        # - Widgets
        # -- Groupboxes
        self.groupbox_jamo = QtGui.QGroupBox(JAMO_LABEL_KO[jamoIdx])
        
        self.btnGrp_jamo = QtGui.QButtonGroup()
        self.btnGrp_jamo.setExclusive(False)

        self.btnGrp_jamo.buttonToggled.connect(self.updateJamoSelection)

        self.gridLayout_jamo = QtGui.QGridLayout()
        self.gridLayout_jamo.setSpacing(1)
        self.gridLayout_jamo.setVerticalSpacing(1)

        self.hSpacer30 = QtGui.QSpacerItem(1, 30)
        self.hSpacer20 = QtGui.QSpacerItem(1, 20)
        self.hSpacer10 = QtGui.QSpacerItem(1, 10)

        for idx, chr in enumerate(JAMO_LIST[jamoIdx]):
            if jamoIdx == 2 and chr == '':
                chr = u'·'
            exec("""
self.btn_jamo_{idx} = QtGui.QPushButton(chr)
self.btn_jamo_{idx}.setCheckable(True)
self.gridLayout_jamo.addWidget(self.btn_jamo_{idx}, idx//7, idx%7, 1, 1, QtCore.Qt.AlignTop)
self.btnGrp_jamo.addButton(self.btn_jamo_{idx}, {idx})
""".format(idx = idx))

        self.gridLayout_jamo.addItem(self.hSpacer30, 3, 1)
        self.groupbox_jamo.setLayout(self.gridLayout_jamo)

        # -- List
        self.enlistedJamo_List = ListWidget(self, self.jamoIdx)
        
        # -- Buttons
        self.btn_selectAll_jamo = QtGui.QPushButton('전체 선택')
        self.btn_unselectAll_jamo = QtGui.QPushButton('선택 해제')
        self.btn_selectReverse_jamo = QtGui.QPushButton('선택 반전')
        self.btn_enlistComp_jamo = QtGui.QPushButton('등록')
        self.btn_modComp_jamo = QtGui.QPushButton('변경')
        self.btn_removeComp_jamo = QtGui.QPushButton('삭제')

        # -- Tooltips
        self.btn_selectAll_jamo.setToolTip(u'전체 자소를 선택합니다.')
        self.btn_unselectAll_jamo.setToolTip(u'자소 선택을 해제합니다.')
        self.btn_selectReverse_jamo.setToolTip(u'자소 선택을 반전합니다.')
        self.btn_enlistComp_jamo.setToolTip(u'현재 자소를 등록합니다.')
        self.btn_modComp_jamo.setToolTip(u'선택한 자소를 수정합니다.')
        self.btn_removeComp_jamo.setToolTip(u'선택한 자소를 삭제합니다.')

        # -- Slots
        self.btn_selectAll_jamo.clicked.connect(self.selectAllJamo)
        self.btn_unselectAll_jamo.clicked.connect(self.unselectAllJamo)
        self.btn_selectReverse_jamo.clicked.connect(self.reverseJamoSelection)
        
        self.btn_enlistComp_jamo.clicked.connect(self.enlistedJamo_List.addCompItems)
        self.btn_modComp_jamo.clicked.connect(self.enlistedJamo_List.modifyCompItems)
        self.btn_removeComp_jamo.clicked.connect(self.enlistedJamo_List.removeCompItems)

        # -- Build Layout
        self.layout_jamo = QtGui.QGridLayout()

        self.layout_jamo.addWidget(self.groupbox_jamo,           0,0,1,3)

        self.layout_jamo.addWidget(self.btn_selectAll_jamo,      1,0,1,1)
        self.layout_jamo.addWidget(self.btn_unselectAll_jamo,    1,1,1,1)
        self.layout_jamo.addWidget(self.btn_selectReverse_jamo,  1,2,1,1)

        self.layout_jamo.addItem(self.hSpacer20, 2, 0)

        self.layout_jamo.addWidget(self.enlistedJamo_List,       3,0,4,3)
        self.layout_jamo.addWidget(self.btn_enlistComp_jamo,     7,0,1,1)
        self.layout_jamo.addWidget(self.btn_modComp_jamo,        7,1,1,1)
        self.layout_jamo.addWidget(self.btn_removeComp_jamo,     7,2,1,1)

        self.layout_jamo.addItem(self.hSpacer20, 8, 0)
        # - StyleSheet
        jasoBtnStyleSheet ='''
QGroupBox > QPushButton{
    font-weight: 400;
    font-size: 17px;
    margin: 0;
    width: 40px;
    height: 30px;
}'''
        self.groupbox_jamo.setStyleSheet(jasoBtnStyleSheet)
        self.layout_jamo.setSpacing(0)
        self.layout_jamo.setVerticalSpacing(5)
        self.setLayout(self.layout_jamo)

        self.readJamoGroups()

        # - Methods
    def updateJamoSelection(self): #btn, state):
        self.selected_jamo = []
        for button in self.btnGrp_jamo.buttons():
            if button.isChecked():
                self.selected_jamo.append(button.text)
        # print(456, self.selected_jamo)

    def updateBtnSelection(self): #btn, state):
        buttons_to_manipulate = self.selected_jamo
        for button in self.btnGrp_jamo.buttons():
            if button.text in buttons_to_manipulate:
                button.setChecked(True)
            else: 
                button.setChecked(False)
        # print(500, self.selected_jamo)

    def reverseJamoSelection(self): #btn, state):
        self.selected_jamo = []
        for button in self.btnGrp_jamo.buttons():
            if button.isChecked():
                button.setChecked(False)
            else: 
                button.setChecked(True)
        # print(509, self.selected_jamo)

    def unselectAllJamo(self):
        self.selected_jamo = []
        for button in self.btnGrp_jamo.buttons():
            button.setChecked(False)
        # print(462, self.selected_jamo)

    def selectAllJamo(self):
        self.selected_jamo = []
        for button in self.btnGrp_jamo.buttons():
            button.setChecked(True)
        # print(521, self.selected_jamo)

    def writeJamoGroups(self):
        jamoGroupList = []
        for x in range(self.enlistedJamo_List.count):
            jamoGroupList.append({self.enlistedJamo_List.item(x).text():self.enlistedJamo_List.item(x).data(256)})
        # print(527, jamoGroupList)
        # print(528, JAMO_GROUP_DICT)
        JAMO_GROUP_DICT[JAMO_LABEL_EN[self.jamoIdx]] = jamoGroupList
        NEW_JAMO_DICT = flP.packageLib
        NEW_JAMO_DICT["com.Minwoo.GenerateHangeulComposition"][JAMO_LABEL_EN[self.jamoIdx]] = JAMO_GROUP_DICT[JAMO_LABEL_EN[self.jamoIdx]]
        flP.packageLib = NEW_JAMO_DICT
        # print(533, flP.packageLib["com.Minwoo.GenerateHangeulComposition"])

    def readJamoGroups(self):
        jamoGroupList = JAMO_GROUP_DICT[JAMO_LABEL_EN[self.jamoIdx]]
        for group in jamoGroupList:
            item = QtGui.QListWidgetItem()
            item.setData(256, list(group.values())[0])
            item.setText(list(group.keys())[0])
            item.setFlags(1|2|16|32) # ItemIsSelectable | ItemIsEditable | ItemIsEnabled
            self.enlistedJamo_List.addItem(item)


class MainWindow(QtGui.QWidget):
    # - Split/Break contour 
    def __init__(self):
        super(MainWindow, self).__init__()

        # - Init
        self.composedChars = []
        self.setStyleSheet(styleSheet)

        # - Widgets
        # -- Groupboxes
        self.groupbox_controls = QtGui.QGroupBox('')

        self.gridLayout_controls = QtGui.QGridLayout()

        self.gridLayout_controls.setSpacing(0)
        self.gridLayout_controls.setVerticalSpacing(0)

        self.hSpacer30 = QtGui.QSpacerItem(1, 30)
        self.hSpacer20 = QtGui.QSpacerItem(1, 20)
        self.hSpacer10 = QtGui.QSpacerItem(1, 10)

        self.groupbox_controls.setLayout(self.gridLayout_controls)
        
        self.ChoWidget = JamoWidget(0)
        self.JungWidget = JamoWidget(1)
        self.JongWidget = JamoWidget(2)

        # -- Buttons
        self.btn_copy = QtGui.QPushButton(u'복사')
        self.btn_editOnCurTab = QtGui.QPushButton(u'현재 창')
        self.btn_editOnNewTab = QtGui.QPushButton(u'새 창')
        self.btn_compose = QtGui.QPushButton(u'조합하기')
        self.btn_close = QtGui.QPushButton(u'종료')

        # -- ComboBoxes
        self.comboBox_charRange = QtGui.QComboBox()
        self.label_charRange = QtGui.QLabel(u'조합 범위 :')
        self.comboBox_charRange.addItem(u'ADOBE-KR-9 - 2780자', 0)
        self.comboBox_charRange.addItem(u'KS X 1001 - 2350자', 1)
        self.comboBox_charRange.addItem(u'현대 한글 - 11172자', 2)
        self.comboBox_charRange.addItem(u'확장 음절 - 8392자', 3)

        self.comboBox_sortOrder = QtGui.QComboBox()
        self.label_sortOrder = QtGui.QLabel(u'정렬 순서 :')
        self.comboBox_sortOrder.addItem(u'초성 순', 0)
        self.comboBox_sortOrder.addItem(u'중성 순', 1)
        self.comboBox_sortOrder.addItem(u'종성 순', 2)

        # -- CheckBoxes 
        self.chkbox_sortByJung = QtGui.QCheckBox('중성 모임꼴 순 정렬')
        self.chkbox_lineBreak = QtGui.QCheckBox('중성별 줄바꿈')

        # -- Tooltips
        self.btn_copy.setToolTip(u'클립보드에 조합된 문자열을 복사합니다.')
        self.btn_editOnCurTab.setToolTip(u'조합된 문자열을 현재 글리프 윈도우에서 편집합니다.')
        self.btn_editOnNewTab.setToolTip(u'조합된 문자열을 새 글리프 윈도우에서 편집합니다.')
        self.chkbox_sortByJung.setToolTip(u'모임꼴 순으로 중성을 정렬합니다.')
        self.chkbox_lineBreak.setToolTip(u'조합된 문자열을 중성별로 줄바꿈합니다.')
        self.btn_compose.setToolTip(u'선택한 자소를 조합합니다.')
        self.btn_close.setToolTip(u'스크립트를 종료합니다.')
        self.comboBox_charRange.setToolTip(u'조합할 한글의 범위를 선택합니다.')
        self.comboBox_sortOrder.setToolTip(u'조합된 문자열의 정렬 순서를 선택합니다.')

        # -- Slots
        self.btn_editOnCurTab.clicked.connect(self.editOnCurTab)
        self.btn_editOnNewTab.clicked.connect(self.editOnNewTab)
        self.chkbox_sortByJung.stateChanged.connect(self.sortJungByType)
        self.chkbox_lineBreak.stateChanged.connect(self.breakLineOnJung)

        self.btn_compose.clicked.connect(self.refreshText)
        self.comboBox_charRange.currentIndexChanged.connect(self.charRangeChanged)
        self.comboBox_sortOrder.currentIndexChanged.connect(self.sortOrderChanged)
        self.btn_close.clicked.connect(self.closeWidget)
        self.btn_copy.clicked.connect(self.copyComposedStr)

        # -- TextEdit
        self.textEdit_output = QtGui.QTextEdit()
        self.textEdit_output.setReadOnly(True)
        self.label_strLen = QtGui.QLabel('조합된 글자')
        
        # -- Build Layout
        self.layout_main = QtGui.QGridLayout()
        self.layout_main.addWidget(self.ChoWidget,           0,0,8,3)
        self.layout_main.addWidget(self.JungWidget,          0,3,8,3)
        self.layout_main.addWidget(self.JongWidget,          0,6,8,3)

        self.layout_main.addWidget(self.textEdit_output,        9,0,4,6)
        self.layout_main.addWidget(self.chkbox_sortByJung,      13,2,1,2)
        self.layout_main.addWidget(self.chkbox_lineBreak,       13,4,1,2)
        self.layout_main.addWidget(self.label_strLen,           13,0,1,2)
        self.layout_main.addWidget(self.groupbox_controls,      9,6,5,3)

        self.gridLayout_controls.addWidget(self.label_charRange,        0,0,1,1)
        self.gridLayout_controls.addWidget(self.comboBox_charRange,     0,1,1,2)
        self.gridLayout_controls.addWidget(self.label_sortOrder,        1,0,1,1)
        self.gridLayout_controls.addWidget(self.comboBox_sortOrder,     1,1,1,2)
        
        self.gridLayout_controls.addWidget(self.btn_compose,            2,0,1,3)
        self.gridLayout_controls.addWidget(self.btn_copy,               3,0,1,1)
        self.gridLayout_controls.addWidget(self.btn_editOnCurTab,       3,1,1,1)
        self.gridLayout_controls.addWidget(self.btn_editOnNewTab,       3,2,1,1)
        self.gridLayout_controls.addWidget(self.btn_close,              4,0,1,3)
        # self.gridLayout_controls.addItem(self.hSpacer10, 5, 1)

        self.layout_main.setSpacing(0)
        self.layout_main.setVerticalSpacing(5)
        self.setLayout(self.layout_main)

        # - StyleSheet
        self.btn_compose.setStyleSheet('''
        QPushButton{
            background-color: #3585fd;
            color: white;
            font-weight: 400;
            font-size: 16px;
            border-radius: 5px;
            border: 1px outset #2a6aca;
            height: 35px;
        }
        QPushButton:pressed{
            background-color: #2d77e2;
        }
        ''')

        # - Set Widget
        self.setWindowTitle('%s %s' %(app_name, app_version))
        self.setGeometry(0, 0, 900, 400)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint) # Always on top!!
        self.move(qapp.desktop().availableGeometry().width() / 2 - 900 / 2, qapp.desktop().availableGeometry().height() / 2 - 800 / 2) # move window to visible desktop center
        self.setMinimumSize(500,self.sizeHint.height())

        self.show()

    def refreshText(self):
        if is_cho(self.ChoWidget.selected_jamo)==[] and is_jung(self.JungWidget.selected_jamo)==[] and is_jong(self.JongWidget.selected_jamo)==[] :
            QtGui.QMessageBox.information(self, "알림", "선택된 자소가 없습니다.")
        self.composedChars = composeAllCases(self.ChoWidget.selected_jamo, self.JungWidget.selected_jamo, self.JongWidget.selected_jamo, SORT_JUNG_BY_TYPE, LINE_BREAK)
        self.textEdit_output.setText(''.join(self.composedChars))
        self.label_strLen.setText('조합된 글자: {}자'.format(len(self.textEdit_output.toPlainText().replace('\n',''))))

    def stringExists(self):
        if self.textEdit_output.toPlainText():
            return True
        else: 
            return False

    def charRangeChanged(self):
        global CHAR_RANGE
        CHAR_RANGE = self.comboBox_charRange.currentData
        if self.stringExists():
            self.refreshText()

    def sortOrderChanged(self):
        global SORT_ORDER 
        SORT_ORDER = self.comboBox_sortOrder.currentData
        if self.stringExists():
            self.refreshText()

    def editOnNewTab(self):
        if self.stringExists():
            editOnCanvas(self.composedChars, True)
        else: 
            print('조합된 문자열이 없습니다.')
            return

    def editOnCurTab(self):
        if self.stringExists():
            if fl6.flWorkspace.instance().getActiveCanvas():
                editOnCanvas(self.composedChars, False)
            else: 
                print(u'현재 열린 글리프 윈도우가 없습니다.')
        else: 
            print('조합된 문자열이 없습니다.')
            return

    def breakLineOnJung(self):
        global LINE_BREAK
        LINE_BREAK = not LINE_BREAK
        if self.stringExists():
            self.refreshText()
            
    def sortJungByType(self):
        global SORT_JUNG_BY_TYPE
        SORT_JUNG_BY_TYPE = not SORT_JUNG_BY_TYPE
        if self.stringExists():
            self.refreshText()

    def copyComposedStr(self):
        if self.stringExists():
            copy2clip(self.textEdit_output.toPlainText()) 

    def closeWidget(self):
        self.close()

# - RUN ------------------------------
dialog1 = MainWindow()
