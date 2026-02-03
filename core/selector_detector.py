"""
智能选择器探测器
自动分析页面结构并生成CSS选择器
"""
import re
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from collections import Counter
from loguru import logger
from urllib.parse import urlparse


class SelectorDetector:
    """智能选择器探测器"""
    
    def __init__(self):
        self.confidence_threshold = 0.7  # 置信度阈值
    
    def detect_forum_type(self, html: str, url: str) -> str:
        """
        检测论坛类型
        
        Args:
            html: HTML内容
            url: 页面URL
        
        Returns:
            论坛类型（discuz, phpbb, custom等）
        """
        html_lower = html.lower()
        
        # Discuz论坛特征
        if 'discuz' in html_lower or 'powered by discuz' in html_lower:
            logger.info("✓ 检测到 Discuz 论坛")
            return 'discuz'
        
        # phpBB论坛特征
        if 'phpbb' in html_lower or 'powered by phpbb' in html_lower:
            logger.info("✓ 检测到 phpBB 论坛")
            return 'phpbb'
        
        # vBulletin论坛特征
        if 'vbulletin' in html_lower:
            logger.info("✓ 检测到 vBulletin 论坛")
            return 'vbulletin'
        
        logger.info("✓ 检测到自定义论坛系统")
        return 'custom'
    
    def detect_thread_list_selector(self, html: str, forum_type: str = 'custom') -> Tuple[str, float]:
        """
        检测帖子列表选择器
        
        Args:
            html: HTML内容
            forum_type: 论坛类型
        
        Returns:
            (选择器, 置信度)
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # 根据论坛类型使用预设选择器
        if forum_type == 'discuz':
            selector = "tbody[id^='normalthread'], tbody[id^='stickthread']"
            elements = soup.select(selector)
            if elements:
                confidence = min(1.0, len(elements) / 20)  # 假设每页20个帖子
                logger.info(f"✓ Discuz帖子列表: {len(elements)}个元素, 置信度: {confidence:.2f}")
                return selector, confidence
        
        elif forum_type == 'phpbb':
            selector = "li.row"
            elements = soup.select(selector)
            if elements:
                confidence = min(1.0, len(elements) / 20)
                logger.info(f"✓ phpBB帖子列表: {len(elements)}个元素, 置信度: {confidence:.2f}")
                return selector, confidence
        
        # 通用检测逻辑
        candidates = []
        
        # 候选模式1: 包含thread/topic关键词的class
        for pattern in [r'thread', r'topic', r'post-item', r'list-item']:
            elements = soup.find_all(class_=re.compile(pattern, re.I))
            if 5 <= len(elements) <= 50:  # 合理的帖子数量范围
                selector = self._generate_class_selector(elements[0])
                candidates.append({
                    'selector': selector,
                    'count': len(elements),
                    'confidence': self._calculate_list_confidence(elements)
                })
        
        # 候选模式2: 包含thread/topic关键词的id
        for pattern in [r'thread', r'topic']:
            elements = soup.find_all(id=re.compile(pattern, re.I))
            if 5 <= len(elements) <= 50:
                selector = self._generate_id_selector(elements[0])
                candidates.append({
                    'selector': selector,
                    'count': len(elements),
                    'confidence': self._calculate_list_confidence(elements)
                })
        
        # 候选模式3: 重复的结构模式
        tag_patterns = self._find_repeated_patterns(soup)
        for tag, attrs, count in tag_patterns:
            if 5 <= count <= 50:
                selector = self._generate_pattern_selector(tag, attrs)
                candidates.append({
                    'selector': selector,
                    'count': count,
                    'confidence': min(1.0, count / 20)
                })
        
        # 选择最佳候选
        if candidates:
            best = max(candidates, key=lambda x: x['confidence'])
            logger.info(f"✓ 检测到帖子列表: {best['selector']}, 数量: {best['count']}, 置信度: {best['confidence']:.2f}")
            return best['selector'], best['confidence']
        
        logger.warning("✗ 未能检测到帖子列表选择器")
        return "", 0.0
    
    def detect_thread_link_selector(self, html: str, list_selector: str) -> Tuple[str, float]:
        """
        检测帖子链接选择器
        
        Args:
            html: HTML内容
            list_selector: 已检测到的列表选择器
        
        Returns:
            (选择器, 置信度)
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # 在列表元素内查找链接
        list_elements = soup.select(list_selector) if list_selector else soup.find_all()
        
        if not list_elements:
            logger.warning("✗ 无法定位列表元素")
            return "", 0.0
        
        # 分析第一个列表元素中的链接
        first_element = list_elements[0]
        links = first_element.find_all('a', href=True)
        
        candidates = []
        for link in links:
            # 检查是否可能是帖子链接
            href = link.get('href', '')
            
            # 排除不太可能是帖子的链接
            if any(x in href.lower() for x in ['javascript:', '#', 'user', 'member', 'avatar']):
                continue
            
            # 检查是否包含thread/topic等关键词
            if any(x in href.lower() for x in ['thread', 'topic', 'viewthread', 't/', 'tid=']):
                selector = self._generate_link_selector(link, first_element)
                confidence = 0.9
                candidates.append({
                    'selector': selector,
                    'confidence': confidence,
                    'href': href
                })
        
        # 如果没有明确的thread链接，选择最显眼的链接
        if not candidates and links:
            largest_link = max(links, key=lambda x: len(x.get_text(strip=True)))
            selector = self._generate_link_selector(largest_link, first_element)
            candidates.append({
                'selector': selector,
                'confidence': 0.6,
                'href': largest_link.get('href', '')
            })
        
        if candidates:
            best = max(candidates, key=lambda x: x['confidence'])
            logger.info(f"✓ 检测到帖子链接: {best['selector']}, 置信度: {best['confidence']:.2f}")
            return best['selector'], best['confidence']
        
        logger.warning("✗ 未能检测到帖子链接选择器")
        return "a", 0.3  # 默认返回第一个链接
    
    def detect_image_selector(self, html: str) -> Tuple[str, float]:
        """
        检测图片选择器
        
        Args:
            html: HTML内容
        
        Returns:
            (选择器, 置信度)
        """
        soup = BeautifulSoup(html, 'lxml')
        
        selectors = []
        
        # 方法1: 查找所有img标签
        all_imgs = soup.find_all('img')
        content_imgs = [img for img in all_imgs if self._is_content_image(img)]
        
        if content_imgs:
            # 分析这些图片的共同特征
            classes = []
            for img in content_imgs:
                if img.get('class'):
                    classes.extend(img['class'])
            
            if classes:
                common_class = Counter(classes).most_common(1)[0][0]
                selector = f"img.{common_class}"
                confidence = min(1.0, len(content_imgs) / 10)
                selectors.append((selector, confidence))
        
        # 方法2: 常见的内容图片选择器
        common_patterns = [
            "div.content img",
            "div.post-content img",
            "div.message img",
            "article img",
            "div.postcontent img",
            "div.t_fsz img",
            "img.zoom",
            "img[file]",
        ]
        
        for pattern in common_patterns:
            elements = soup.select(pattern)
            if elements:
                confidence = min(1.0, len(elements) / 5)
                selectors.append((pattern, confidence))
        
        # 方法3: 查找src包含图片扩展名的img
        img_pattern = r'\.(jpg|jpeg|png|gif|webp|bmp)'
        imgs_with_ext = [
            img for img in all_imgs 
            if img.get('src') and re.search(img_pattern, img['src'], re.I)
        ]
        
        if imgs_with_ext and not selectors:
            selector = "img[src]"
            confidence = 0.5
            selectors.append((selector, confidence))
        
        if selectors:
            best = max(selectors, key=lambda x: x[1])
            logger.info(f"✓ 检测到图片选择器: {best[0]}, 置信度: {best[1]:.2f}")
            return best
        
        logger.warning("✗ 未能检测到图片选择器")
        return "img", 0.3
    
    def detect_next_page_selector(self, html: str) -> Tuple[str, float]:
        """
        检测下一页选择器
        
        Args:
            html: HTML内容
        
        Returns:
            (选择器, 置信度)
        """
        soup = BeautifulSoup(html, 'lxml')
        
        candidates = []
        
        # 方法1: 查找包含"下一页"、"next"等文字的链接
        next_keywords = ['下一页', '下一頁', 'next', 'next page', '›', '»', '&gt;']
        
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True).lower()
            if any(keyword.lower() in text for keyword in next_keywords):
                selector = self._generate_link_selector(link)
                confidence = 0.9
                candidates.append((selector, confidence))
                break
        
        # 方法2: 常见的下一页class/id
        common_patterns = [
            "a.next",
            "a.nxt",
            "a.next-page",
            "a[rel='next']",
            "li.next a",
            "div.pagination a.next",
        ]
        
        for pattern in common_patterns:
            elements = soup.select(pattern)
            if elements:
                confidence = 0.8
                candidates.append((pattern, confidence))
                break
        
        if candidates:
            best = max(candidates, key=lambda x: x[1])
            logger.info(f"✓ 检测到下一页选择器: {best[0]}, 置信度: {best[1]:.2f}")
            return best
        
        logger.warning("✗ 未能检测到下一页选择器")
        return "", 0.0
    
    def auto_detect_selectors(self, html: str, url: str) -> Dict[str, any]:
        """
        自动检测所有选择器
        
        Args:
            html: HTML内容
            url: 页面URL
        
        Returns:
            包含所有选择器的字典
        """
        logger.info("=" * 60)
        logger.info("开始自动检测页面选择器")
        logger.info(f"URL: {url}")
        logger.info("=" * 60)
        
        # 检测论坛类型
        forum_type = self.detect_forum_type(html, url)
        
        # 检测各个选择器
        thread_list_selector, thread_list_conf = self.detect_thread_list_selector(html, forum_type)
        thread_link_selector, thread_link_conf = self.detect_thread_link_selector(html, thread_list_selector)
        image_selector, image_conf = self.detect_image_selector(html)
        next_page_selector, next_page_conf = self.detect_next_page_selector(html)
        
        # 计算总体置信度
        avg_confidence = (
            thread_list_conf + thread_link_conf + 
            image_conf + next_page_conf
        ) / 4
        
        result = {
            'forum_type': forum_type,
            'selectors': {
                'thread_list_selector': thread_list_selector,
                'thread_link_selector': thread_link_selector,
                'image_selector': image_selector,
                'next_page_selector': next_page_selector,
            },
            'confidence': {
                'thread_list': thread_list_conf,
                'thread_link': thread_link_conf,
                'image': image_conf,
                'next_page': next_page_conf,
                'overall': avg_confidence,
            },
            'status': 'success' if avg_confidence >= self.confidence_threshold else 'uncertain'
        }
        
        logger.info("=" * 60)
        logger.info(f"检测完成! 总体置信度: {avg_confidence:.2%}")
        logger.info("=" * 60)
        
        return result
    
    # ==================== 辅助方法 ====================
    
    def _is_content_image(self, img) -> bool:
        """判断是否是内容图片（非头像、图标等）"""
        src = img.get('src', '').lower()
        
        # 排除明显的非内容图片
        exclude_patterns = ['avatar', 'icon', 'logo', 'banner', 'smilie', 'emoji']
        if any(p in src for p in exclude_patterns):
            return False
        
        # 检查尺寸属性
        width = img.get('width', '')
        height = img.get('height', '')
        
        try:
            if width and int(width) < 100:
                return False
            if height and int(height) < 100:
                return False
        except:
            pass
        
        return True
    
    def _generate_class_selector(self, element) -> str:
        """根据元素生成class选择器"""
        classes = element.get('class', [])
        if classes:
            return f"{element.name}.{classes[0]}"
        return element.name
    
    def _generate_id_selector(self, element) -> str:
        """根据元素生成id选择器"""
        elem_id = element.get('id', '')
        if elem_id:
            # 提取id的模式部分
            match = re.match(r'([a-zA-Z_-]+)', elem_id)
            if match:
                pattern = match.group(1)
                return f"{element.name}[id^='{pattern}']"
        return element.name
    
    def _generate_pattern_selector(self, tag: str, attrs: dict) -> str:
        """根据标签和属性生成选择器"""
        if 'class' in attrs and attrs['class']:
            return f"{tag}.{attrs['class'][0]}"
        elif 'id' in attrs:
            return f"{tag}#{attrs['id']}"
        return tag
    
    def _generate_link_selector(self, link, parent=None) -> str:
        """生成链接选择器"""
        classes = link.get('class', [])
        
        if classes:
            return f"a.{'.'.join(classes)}"
        
        # 尝试使用相对位置
        if parent:
            parent_classes = parent.get('class', [])
            if parent_classes:
                return f".{parent_classes[0]} a"
        
        return "a"
    
    def _calculate_list_confidence(self, elements: list) -> float:
        """计算列表置信度"""
        if not elements:
            return 0.0
        
        count = len(elements)
        
        # 基于数量的置信度
        if 10 <= count <= 30:
            base_confidence = 0.9
        elif 5 <= count < 10:
            base_confidence = 0.7
        elif count > 30:
            base_confidence = 0.6
        else:
            base_confidence = 0.4
        
        # 检查结构一致性
        first_structure = str(elements[0])
        similar_count = sum(1 for e in elements if len(str(e)) in range(len(first_structure) - 100, len(first_structure) + 100))
        consistency = similar_count / count
        
        return base_confidence * consistency
    
    def _find_repeated_patterns(self, soup) -> List[Tuple[str, dict, int]]:
        """查找重复的HTML模式"""
        patterns = []
        
        # 统计各种标签+class组合的出现次数
        tag_class_counter = Counter()
        
        for tag in soup.find_all():
            classes = tag.get('class', [])
            if classes:
                key = (tag.name, tuple(classes))
                tag_class_counter[key] += 1
        
        # 返回出现次数较多的模式
        for (tag, classes), count in tag_class_counter.most_common(10):
            if count >= 5:
                patterns.append((tag, {'class': list(classes)}, count))
        
        return patterns
    
    def generate_config_code(self, selectors: Dict) -> str:
        """生成配置代码"""
        code = f"""
# 自动检测的选择器配置
BBSConfig(
    # 论坛类型: {selectors.get('forum_type', 'custom')}
    base_url="需要手动设置",
    
    # 自动检测的选择器（置信度: {selectors['confidence']['overall']:.2%}）
    thread_list_selector="{selectors['selectors']['thread_list_selector']}",
    thread_link_selector="{selectors['selectors']['thread_link_selector']}",
    image_selector="{selectors['selectors']['image_selector']}",
    next_page_selector="{selectors['selectors']['next_page_selector']}",
)
"""
        return code.strip()
