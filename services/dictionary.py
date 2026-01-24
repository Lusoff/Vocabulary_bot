"""Сервис для работы с английским словарём."""
import aiohttp
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Definition:
    """Одно определение слова."""
    definition: str
    example: Optional[str] = None
    synonyms: list = None
    antonyms: list = None
    translation_ru: Optional[str] = None  # Перевод на русский
    
    def __post_init__(self):
        self.synonyms = self.synonyms or []
        self.antonyms = self.antonyms or []


@dataclass
class PartOfSpeech:
    """Часть речи с определениями."""
    part_of_speech: str  # noun, verb, adjective, etc.
    definitions: list[Definition]
    
    # Для глаголов — формы
    verb_forms: Optional[dict] = None  # {past: "ran", past_participle: "run", present_participle: "running"}


@dataclass
class WordInfo:
    """Полная информация о слове."""
    word: str
    phonetic: Optional[str]  # Транскрипция
    phonetic_audio: Optional[str]  # URL аудио произношения
    parts_of_speech: list[PartOfSpeech]
    
    def format_for_telegram(self) -> str:
        """Форматирование для отправки в Telegram."""
        lines = []
        
        # Заголовок со словом и транскрипцией
        header = f"📖 *{self.word}*"
        if self.phonetic:
            header += f"  `{self.phonetic}`"
        lines.append(header)
        lines.append("")
        
        # Части речи и определения
        for pos in self.parts_of_speech:
            pos_emoji = self._get_pos_emoji(pos.part_of_speech)
            lines.append(f"{pos_emoji} *{pos.part_of_speech.upper()}*")
            
            # Формы глагола
            if pos.verb_forms:
                forms = pos.verb_forms
                forms_str = []
                if forms.get("past"):
                    forms_str.append(f"past: _{forms['past']}_")
                if forms.get("past_participle"):
                    forms_str.append(f"p.p.: _{forms['past_participle']}_")
                if forms.get("present_participle"):
                    forms_str.append(f"-ing: _{forms['present_participle']}_")
                if forms_str:
                    lines.append(f"   📝 Forms: {', '.join(forms_str)}")
            
            lines.append("")
            
            # Определения с примерами
            for i, defn in enumerate(pos.definitions[:5], 1):  # Максимум 5 определений
                # Перевод слова для этого значения
                if defn.translation_ru:
                    lines.append(f"   {i}. 🇷🇺 *{defn.translation_ru}*")
                    lines.append(f"      🇬🇧 {defn.definition}")
                else:
                    lines.append(f"   {i}. {defn.definition}")
                
                # Пример использования
                if defn.example:
                    lines.append(f"      💬 _{defn.example}_")
                
                # Синонимы (только первые 3)
                if defn.synonyms:
                    syns = ", ".join(defn.synonyms[:3])
                    lines.append(f"      🔄 Synonyms: {syns}")
                
                lines.append("")
        
        return "\n".join(lines)
    
    def _get_pos_emoji(self, pos: str) -> str:
        """Эмодзи для части речи."""
        emojis = {
            "noun": "📦",
            "verb": "⚡",
            "adjective": "🎨",
            "adverb": "💨",
            "pronoun": "👤",
            "preposition": "📍",
            "conjunction": "🔗",
            "interjection": "❗",
            "determiner": "🎯",
        }
        return emojis.get(pos.lower(), "📌")


class DictionaryService:
    """Сервис для получения информации о словах."""
    
    # Free Dictionary API — для определений и транскрипции
    FREE_DICT_URL = "https://api.dictionaryapi.dev/api/v2/entries/en"
    
    # Yandex Dictionary API — для переводов
    YANDEX_DICT_URL = "https://dictionary.yandex.net/api/v1/dicservice.json/lookup"
    
    def __init__(self, yandex_api_key: str = None):
        """Инициализация сервиса."""
        self.yandex_api_key = yandex_api_key
    
    # Неправильные глаголы (основные)
    IRREGULAR_VERBS = {
        "be": {"past": "was/were", "past_participle": "been", "present_participle": "being"},
        "become": {"past": "became", "past_participle": "become", "present_participle": "becoming"},
        "begin": {"past": "began", "past_participle": "begun", "present_participle": "beginning"},
        "break": {"past": "broke", "past_participle": "broken", "present_participle": "breaking"},
        "bring": {"past": "brought", "past_participle": "brought", "present_participle": "bringing"},
        "build": {"past": "built", "past_participle": "built", "present_participle": "building"},
        "buy": {"past": "bought", "past_participle": "bought", "present_participle": "buying"},
        "catch": {"past": "caught", "past_participle": "caught", "present_participle": "catching"},
        "choose": {"past": "chose", "past_participle": "chosen", "present_participle": "choosing"},
        "come": {"past": "came", "past_participle": "come", "present_participle": "coming"},
        "cost": {"past": "cost", "past_participle": "cost", "present_participle": "costing"},
        "cut": {"past": "cut", "past_participle": "cut", "present_participle": "cutting"},
        "do": {"past": "did", "past_participle": "done", "present_participle": "doing"},
        "draw": {"past": "drew", "past_participle": "drawn", "present_participle": "drawing"},
        "drink": {"past": "drank", "past_participle": "drunk", "present_participle": "drinking"},
        "drive": {"past": "drove", "past_participle": "driven", "present_participle": "driving"},
        "eat": {"past": "ate", "past_participle": "eaten", "present_participle": "eating"},
        "fall": {"past": "fell", "past_participle": "fallen", "present_participle": "falling"},
        "feel": {"past": "felt", "past_participle": "felt", "present_participle": "feeling"},
        "find": {"past": "found", "past_participle": "found", "present_participle": "finding"},
        "fly": {"past": "flew", "past_participle": "flown", "present_participle": "flying"},
        "forget": {"past": "forgot", "past_participle": "forgotten", "present_participle": "forgetting"},
        "get": {"past": "got", "past_participle": "got/gotten", "present_participle": "getting"},
        "give": {"past": "gave", "past_participle": "given", "present_participle": "giving"},
        "go": {"past": "went", "past_participle": "gone", "present_participle": "going"},
        "grow": {"past": "grew", "past_participle": "grown", "present_participle": "growing"},
        "have": {"past": "had", "past_participle": "had", "present_participle": "having"},
        "hear": {"past": "heard", "past_participle": "heard", "present_participle": "hearing"},
        "hide": {"past": "hid", "past_participle": "hidden", "present_participle": "hiding"},
        "hit": {"past": "hit", "past_participle": "hit", "present_participle": "hitting"},
        "hold": {"past": "held", "past_participle": "held", "present_participle": "holding"},
        "keep": {"past": "kept", "past_participle": "kept", "present_participle": "keeping"},
        "know": {"past": "knew", "past_participle": "known", "present_participle": "knowing"},
        "lead": {"past": "led", "past_participle": "led", "present_participle": "leading"},
        "learn": {"past": "learned/learnt", "past_participle": "learned/learnt", "present_participle": "learning"},
        "leave": {"past": "left", "past_participle": "left", "present_participle": "leaving"},
        "let": {"past": "let", "past_participle": "let", "present_participle": "letting"},
        "lie": {"past": "lay", "past_participle": "lain", "present_participle": "lying"},
        "lose": {"past": "lost", "past_participle": "lost", "present_participle": "losing"},
        "make": {"past": "made", "past_participle": "made", "present_participle": "making"},
        "mean": {"past": "meant", "past_participle": "meant", "present_participle": "meaning"},
        "meet": {"past": "met", "past_participle": "met", "present_participle": "meeting"},
        "pay": {"past": "paid", "past_participle": "paid", "present_participle": "paying"},
        "put": {"past": "put", "past_participle": "put", "present_participle": "putting"},
        "read": {"past": "read", "past_participle": "read", "present_participle": "reading"},
        "ride": {"past": "rode", "past_participle": "ridden", "present_participle": "riding"},
        "ring": {"past": "rang", "past_participle": "rung", "present_participle": "ringing"},
        "rise": {"past": "rose", "past_participle": "risen", "present_participle": "rising"},
        "run": {"past": "ran", "past_participle": "run", "present_participle": "running"},
        "say": {"past": "said", "past_participle": "said", "present_participle": "saying"},
        "see": {"past": "saw", "past_participle": "seen", "present_participle": "seeing"},
        "sell": {"past": "sold", "past_participle": "sold", "present_participle": "selling"},
        "send": {"past": "sent", "past_participle": "sent", "present_participle": "sending"},
        "set": {"past": "set", "past_participle": "set", "present_participle": "setting"},
        "show": {"past": "showed", "past_participle": "shown", "present_participle": "showing"},
        "shut": {"past": "shut", "past_participle": "shut", "present_participle": "shutting"},
        "sing": {"past": "sang", "past_participle": "sung", "present_participle": "singing"},
        "sit": {"past": "sat", "past_participle": "sat", "present_participle": "sitting"},
        "sleep": {"past": "slept", "past_participle": "slept", "present_participle": "sleeping"},
        "speak": {"past": "spoke", "past_participle": "spoken", "present_participle": "speaking"},
        "spend": {"past": "spent", "past_participle": "spent", "present_participle": "spending"},
        "stand": {"past": "stood", "past_participle": "stood", "present_participle": "standing"},
        "steal": {"past": "stole", "past_participle": "stolen", "present_participle": "stealing"},
        "swim": {"past": "swam", "past_participle": "swum", "present_participle": "swimming"},
        "take": {"past": "took", "past_participle": "taken", "present_participle": "taking"},
        "teach": {"past": "taught", "past_participle": "taught", "present_participle": "teaching"},
        "tell": {"past": "told", "past_participle": "told", "present_participle": "telling"},
        "think": {"past": "thought", "past_participle": "thought", "present_participle": "thinking"},
        "throw": {"past": "threw", "past_participle": "thrown", "present_participle": "throwing"},
        "understand": {"past": "understood", "past_participle": "understood", "present_participle": "understanding"},
        "wake": {"past": "woke", "past_participle": "woken", "present_participle": "waking"},
        "wear": {"past": "wore", "past_participle": "worn", "present_participle": "wearing"},
        "win": {"past": "won", "past_participle": "won", "present_participle": "winning"},
        "withdraw": {"past": "withdrew", "past_participle": "withdrawn", "present_participle": "withdrawing"},
        "write": {"past": "wrote", "past_participle": "written", "present_participle": "writing"},
        # Дополнительные
        "arise": {"past": "arose", "past_participle": "arisen", "present_participle": "arising"},
        "awake": {"past": "awoke", "past_participle": "awoken", "present_participle": "awaking"},
        "bear": {"past": "bore", "past_participle": "born/borne", "present_participle": "bearing"},
        "beat": {"past": "beat", "past_participle": "beaten", "present_participle": "beating"},
        "bend": {"past": "bent", "past_participle": "bent", "present_participle": "bending"},
        "bet": {"past": "bet", "past_participle": "bet", "present_participle": "betting"},
        "bind": {"past": "bound", "past_participle": "bound", "present_participle": "binding"},
        "bite": {"past": "bit", "past_participle": "bitten", "present_participle": "biting"},
        "bleed": {"past": "bled", "past_participle": "bled", "present_participle": "bleeding"},
        "blow": {"past": "blew", "past_participle": "blown", "present_participle": "blowing"},
        "breed": {"past": "bred", "past_participle": "bred", "present_participle": "breeding"},
        "broadcast": {"past": "broadcast", "past_participle": "broadcast", "present_participle": "broadcasting"},
        "burst": {"past": "burst", "past_participle": "burst", "present_participle": "bursting"},
        "cast": {"past": "cast", "past_participle": "cast", "present_participle": "casting"},
        "cling": {"past": "clung", "past_participle": "clung", "present_participle": "clinging"},
        "creep": {"past": "crept", "past_participle": "crept", "present_participle": "creeping"},
        "deal": {"past": "dealt", "past_participle": "dealt", "present_participle": "dealing"},
        "dig": {"past": "dug", "past_participle": "dug", "present_participle": "digging"},
        "dive": {"past": "dove/dived", "past_participle": "dived", "present_participle": "diving"},
        "feed": {"past": "fed", "past_participle": "fed", "present_participle": "feeding"},
        "fight": {"past": "fought", "past_participle": "fought", "present_participle": "fighting"},
        "flee": {"past": "fled", "past_participle": "fled", "present_participle": "fleeing"},
        "fling": {"past": "flung", "past_participle": "flung", "present_participle": "flinging"},
        "forbid": {"past": "forbade", "past_participle": "forbidden", "present_participle": "forbidding"},
        "forgive": {"past": "forgave", "past_participle": "forgiven", "present_participle": "forgiving"},
        "freeze": {"past": "froze", "past_participle": "frozen", "present_participle": "freezing"},
        "grind": {"past": "ground", "past_participle": "ground", "present_participle": "grinding"},
        "hang": {"past": "hung", "past_participle": "hung", "present_participle": "hanging"},
        "kneel": {"past": "knelt", "past_participle": "knelt", "present_participle": "kneeling"},
        "lay": {"past": "laid", "past_participle": "laid", "present_participle": "laying"},
        "lean": {"past": "leaned/leant", "past_participle": "leaned/leant", "present_participle": "leaning"},
        "leap": {"past": "leaped/leapt", "past_participle": "leaped/leapt", "present_participle": "leaping"},
        "lend": {"past": "lent", "past_participle": "lent", "present_participle": "lending"},
        "light": {"past": "lit", "past_participle": "lit", "present_participle": "lighting"},
        "overcome": {"past": "overcame", "past_participle": "overcome", "present_participle": "overcoming"},
        "overtake": {"past": "overtook", "past_participle": "overtaken", "present_participle": "overtaking"},
        "prove": {"past": "proved", "past_participle": "proven/proved", "present_participle": "proving"},
        "quit": {"past": "quit", "past_participle": "quit", "present_participle": "quitting"},
        "seek": {"past": "sought", "past_participle": "sought", "present_participle": "seeking"},
        "shake": {"past": "shook", "past_participle": "shaken", "present_participle": "shaking"},
        "shine": {"past": "shone", "past_participle": "shone", "present_participle": "shining"},
        "shoot": {"past": "shot", "past_participle": "shot", "present_participle": "shooting"},
        "shrink": {"past": "shrank", "past_participle": "shrunk", "present_participle": "shrinking"},
        "sink": {"past": "sank", "past_participle": "sunk", "present_participle": "sinking"},
        "slide": {"past": "slid", "past_participle": "slid", "present_participle": "sliding"},
        "sow": {"past": "sowed", "past_participle": "sown/sowed", "present_participle": "sowing"},
        "spin": {"past": "spun", "past_participle": "spun", "present_participle": "spinning"},
        "spit": {"past": "spat", "past_participle": "spat", "present_participle": "spitting"},
        "split": {"past": "split", "past_participle": "split", "present_participle": "splitting"},
        "spread": {"past": "spread", "past_participle": "spread", "present_participle": "spreading"},
        "spring": {"past": "sprang", "past_participle": "sprung", "present_participle": "springing"},
        "stick": {"past": "stuck", "past_participle": "stuck", "present_participle": "sticking"},
        "sting": {"past": "stung", "past_participle": "stung", "present_participle": "stinging"},
        "stink": {"past": "stank", "past_participle": "stunk", "present_participle": "stinking"},
        "strike": {"past": "struck", "past_participle": "struck/stricken", "present_participle": "striking"},
        "strive": {"past": "strove", "past_participle": "striven", "present_participle": "striving"},
        "swear": {"past": "swore", "past_participle": "sworn", "present_participle": "swearing"},
        "sweep": {"past": "swept", "past_participle": "swept", "present_participle": "sweeping"},
        "swing": {"past": "swung", "past_participle": "swung", "present_participle": "swinging"},
        "tear": {"past": "tore", "past_participle": "torn", "present_participle": "tearing"},
        "thrust": {"past": "thrust", "past_participle": "thrust", "present_participle": "thrusting"},
        "tread": {"past": "trod", "past_participle": "trodden", "present_participle": "treading"},
        "undergo": {"past": "underwent", "past_participle": "undergone", "present_participle": "undergoing"},
        "undertake": {"past": "undertook", "past_participle": "undertaken", "present_participle": "undertaking"},
        "upset": {"past": "upset", "past_participle": "upset", "present_participle": "upsetting"},
        "weave": {"past": "wove", "past_participle": "woven", "present_participle": "weaving"},
        "weep": {"past": "wept", "past_participle": "wept", "present_participle": "weeping"},
        "wind": {"past": "wound", "past_participle": "wound", "present_participle": "winding"},
        "wring": {"past": "wrung", "past_participle": "wrung", "present_participle": "wringing"},
    }
    
    async def lookup(self, word: str) -> Optional[WordInfo]:
        """Поиск слова в словаре."""
        word = word.lower().strip()
        
        try:
            async with aiohttp.ClientSession() as session:
                # 1. Получаем переводы из Yandex Dictionary
                yandex_translations = await self._get_yandex_translations(word, session)
                
                # 2. Получаем определения из Free Dictionary
                async with session.get(f"{self.FREE_DICT_URL}/{word}") as response:
                    if response.status != 200:
                        # Если Free Dictionary не нашёл, используем только Yandex
                        if yandex_translations:
                            return self._build_from_yandex(word, yandex_translations)
                        return None
                    
                    data = await response.json()
                    word_info = self._parse_response(word, data, yandex_translations)
                    return word_info
        except Exception as e:
            print(f"Dictionary API error: {e}")
            return None
    
    async def _get_yandex_translations(self, word: str, session: aiohttp.ClientSession) -> dict:
        """Получение переводов из Yandex Dictionary API."""
        if not self.yandex_api_key:
            return {}
        
        translations = {}  # {part_of_speech: [translations]}
        
        try:
            params = {
                "key": self.yandex_api_key,
                "lang": "en-ru",
                "text": word
            }
            
            async with session.get(self.YANDEX_DICT_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for entry in data.get("def", []):
                        pos = entry.get("pos", "unknown")
                        
                        # Собираем все переводы для этой части речи
                        pos_translations = []
                        for tr in entry.get("tr", []):
                            translation = tr.get("text", "")
                            if translation:
                                # Получаем примеры
                                examples = []
                                for ex in tr.get("ex", []):
                                    ex_text = ex.get("text", "")
                                    ex_tr = ex.get("tr", [{}])[0].get("text", "") if ex.get("tr") else ""
                                    if ex_text:
                                        examples.append({"en": ex_text, "ru": ex_tr})
                                
                                pos_translations.append({
                                    "translation": translation,
                                    "examples": examples,
                                    "synonyms": [s.get("text", "") for s in tr.get("syn", [])]
                                })
                        
                        if pos_translations:
                            if pos not in translations:
                                translations[pos] = []
                            translations[pos].extend(pos_translations)
                            
        except Exception as e:
            print(f"Yandex Dictionary API error: {e}")
        
        return translations
    
    def _build_from_yandex(self, word: str, yandex_translations: dict) -> WordInfo:
        """Создание WordInfo только из данных Yandex (если Free Dictionary не нашёл слово)."""
        parts_of_speech = []
        
        for pos, translations in yandex_translations.items():
            definitions = []
            for tr_data in translations[:5]:
                example_en = None
                if tr_data.get("examples"):
                    example_en = tr_data["examples"][0].get("en")
                
                definitions.append(Definition(
                    definition="",  # Нет определения из Free Dictionary
                    example=example_en,
                    translation_ru=tr_data["translation"],
                    synonyms=tr_data.get("synonyms", [])[:3]
                ))
            
            verb_forms = None
            if pos == "verb":
                verb_forms = self._get_verb_forms(word)
            
            parts_of_speech.append(PartOfSpeech(
                part_of_speech=pos,
                definitions=definitions,
                verb_forms=verb_forms
            ))
        
        return WordInfo(
            word=word,
            phonetic=None,
            phonetic_audio=None,
            parts_of_speech=parts_of_speech
        )
    
    def _parse_response(self, word: str, data: list, yandex_translations: dict) -> Optional[WordInfo]:
        """Парсинг ответа Free Dictionary API и объединение с переводами Yandex."""
        if not data:
            return None
        
        entry = data[0]
        
        # Транскрипция
        phonetic = None
        phonetic_audio = None
        
        # Ищем транскрипцию с аудио
        for p in entry.get("phonetics", []):
            if p.get("text"):
                phonetic = p.get("text")
            if p.get("audio"):
                phonetic_audio = p.get("audio")
                if p.get("text"):
                    phonetic = p.get("text")
                    break
        
        # Если не нашли, берём основную
        if not phonetic:
            phonetic = entry.get("phonetic")
        
        # Части речи
        parts_of_speech = []
        
        # Обрабатываем каждую часть речи
        for meaning in entry.get("meanings", []):
            pos = meaning.get("partOfSpeech", "unknown")
            raw_definitions = meaning.get("definitions", [])[:5]  # Максимум 5 определений
            
            if not raw_definitions:
                continue
            
            # Получаем переводы для этой части речи из Yandex
            yandex_pos_translations = yandex_translations.get(pos, [])
            
            definitions = []
            for i, defn in enumerate(raw_definitions):
                def_text = defn.get("definition", "")
                example = defn.get("example")
                
                # Берём перевод из Yandex (по порядку)
                translation_ru = None
                yandex_example = None
                if i < len(yandex_pos_translations):
                    translation_ru = yandex_pos_translations[i].get("translation")
                    # Если нет примера в Free Dictionary, берём из Yandex
                    if not example and yandex_pos_translations[i].get("examples"):
                        yandex_example = yandex_pos_translations[i]["examples"][0].get("en")
                
                definitions.append(Definition(
                    definition=def_text,
                    example=example or yandex_example,
                    synonyms=defn.get("synonyms", []),
                    antonyms=defn.get("antonyms", []),
                    translation_ru=translation_ru,
                ))
            
            # Если в Yandex больше переводов чем определений — добавляем их
            if len(yandex_pos_translations) > len(raw_definitions):
                for j in range(len(raw_definitions), min(len(yandex_pos_translations), 5)):
                    tr_data = yandex_pos_translations[j]
                    example_en = None
                    if tr_data.get("examples"):
                        example_en = tr_data["examples"][0].get("en")
                    
                    definitions.append(Definition(
                        definition="",
                        example=example_en,
                        translation_ru=tr_data.get("translation"),
                        synonyms=tr_data.get("synonyms", [])[:3]
                    ))
            
            # Формы глагола
            verb_forms = None
            if pos == "verb":
                verb_forms = self._get_verb_forms(word)
            
            parts_of_speech.append(PartOfSpeech(
                part_of_speech=pos,
                definitions=definitions,
                verb_forms=verb_forms,
            ))
        
        # Добавляем части речи, которые есть в Yandex, но нет в Free Dictionary
        existing_pos = {p.part_of_speech for p in parts_of_speech}
        for pos, translations in yandex_translations.items():
            if pos not in existing_pos:
                definitions = []
                for tr_data in translations[:5]:
                    example_en = None
                    if tr_data.get("examples"):
                        example_en = tr_data["examples"][0].get("en")
                    
                    definitions.append(Definition(
                        definition="",
                        example=example_en,
                        translation_ru=tr_data.get("translation"),
                        synonyms=tr_data.get("synonyms", [])[:3]
                    ))
                
                verb_forms = None
                if pos == "verb":
                    verb_forms = self._get_verb_forms(word)
                
                parts_of_speech.append(PartOfSpeech(
                    part_of_speech=pos,
                    definitions=definitions,
                    verb_forms=verb_forms
                ))
        
        return WordInfo(
            word=word,
            phonetic=phonetic,
            phonetic_audio=phonetic_audio,
            parts_of_speech=parts_of_speech,
        )
    
    def _get_verb_forms(self, word: str) -> dict:
        """Получение форм глагола."""
        # Проверяем неправильные глаголы
        if word in self.IRREGULAR_VERBS:
            return self.IRREGULAR_VERBS[word]
        
        # Правильные глаголы — добавляем -ed, -ing
        base = word
        
        # Определяем окончания
        if word.endswith("e"):
            past = word + "d"
            present_participle = word[:-1] + "ing"
        elif word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
            past = word[:-1] + "ied"
            present_participle = word + "ing"
        elif (len(word) >= 2 and 
              word[-1] not in "aeiouwxy" and 
              word[-2] in "aeiou" and 
              (len(word) < 3 or word[-3] not in "aeiou")):
            # Удвоение согласной: stop -> stopped, stopping
            past = word + word[-1] + "ed"
            present_participle = word + word[-1] + "ing"
        else:
            past = word + "ed"
            present_participle = word + "ing"
        
        return {
            "past": past,
            "past_participle": past,
            "present_participle": present_participle,
        }
