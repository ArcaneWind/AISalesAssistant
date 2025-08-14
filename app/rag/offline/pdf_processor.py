from typing import Optional, Dict, Any, List
import logging
from pathlib import Path
import PyPDF2
import pdfplumber
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentContent(BaseModel):
    content: str
    metadata: Dict[str, Any]
    page_count: int
    extraction_method: str
    file_size: int
    processed_at: datetime


class PDFProcessorError(Exception):
    pass


class PDFProcessor:
    def __init__(self):
        self.supported_extensions = {'.pdf'}
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        
    def validate_pdf(self, pdf_path: str) -> bool:
        """验证PDF文件是否可处理"""
        try:
            file_path = Path(pdf_path)
            
            if not file_path.exists():
                raise PDFProcessorError(f"文件不存在: {pdf_path}")
                
            if file_path.suffix.lower() not in self.supported_extensions:
                raise PDFProcessorError(f"不支持的文件格式: {file_path.suffix}")
                
            if file_path.stat().st_size > self.max_file_size:
                raise PDFProcessorError(f"文件过大 (>{self.max_file_size/1024/1024}MB): {pdf_path}")
                
            # 尝试打开PDF验证格式
            with open(pdf_path, 'rb') as file:
                try:
                    reader = PyPDF2.PdfReader(file)
                    _ = len(reader.pages)
                    return True
                except Exception:
                    # 如果PyPDF2失败，尝试pdfplumber
                    try:
                        with pdfplumber.open(pdf_path) as pdf:
                            _ = len(pdf.pages)
                        return True
                    except Exception as e:
                        raise PDFProcessorError(f"无效的PDF文件: {str(e)}")
                        
        except Exception as e:
            logger.error(f"PDF验证失败: {str(e)}")
            return False
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """提取PDF元数据"""
        metadata = {
            'title': None,
            'author': None,
            'subject': None,
            'creator': None,
            'producer': None,
            'creation_date': None,
            'modification_date': None,
            'keywords': None
        }
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                if reader.metadata:
                    pdf_metadata = reader.metadata
                    metadata.update({
                        'title': pdf_metadata.get('/Title'),
                        'author': pdf_metadata.get('/Author'),
                        'subject': pdf_metadata.get('/Subject'),
                        'creator': pdf_metadata.get('/Creator'),
                        'producer': pdf_metadata.get('/Producer'),
                        'creation_date': pdf_metadata.get('/CreationDate'),
                        'modification_date': pdf_metadata.get('/ModDate'),
                        'keywords': pdf_metadata.get('/Keywords')
                    })
                    
        except Exception as e:
            logger.warning(f"元数据提取失败: {str(e)}")
            
        return metadata
    
    def _extract_with_pypdf2(self, pdf_path: str) -> tuple[str, int]:
        """使用PyPDF2提取文本"""
        text_content = []
        
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            page_count = len(reader.pages)
            
            for page_num in range(page_count):
                page = reader.pages[page_num]
                text = page.extract_text()
                if text:
                    text_content.append(text)
                    
        return '\n'.join(text_content), page_count
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> tuple[str, int]:
        """使用pdfplumber提取文本"""
        text_content = []
        
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
                    
        return '\n'.join(text_content), page_count
    
    def _clean_text(self, text: str) -> str:
        """清理提取的文本"""
        if not text:
            return ""
            
        # 移除多余的空白字符
        import re
        
        # 统一换行符
        text = re.sub(r'\r\n|\r', '\n', text)
        
        # 移除多余的空格
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 移除多余的换行符
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 移除首尾空白
        text = text.strip()
        
        return text
    
    async def extract_text(self, pdf_path: str, method: str = 'auto') -> DocumentContent:
        """
        提取PDF文本内容
        
        Args:
            pdf_path: PDF文件路径
            method: 提取方法 ('pypdf2', 'pdfplumber', 'auto')
        
        Returns:
            DocumentContent: 包含文本内容和元数据的对象
        """
        try:
            # 验证PDF文件
            if not self.validate_pdf(pdf_path):
                raise PDFProcessorError(f"PDF文件验证失败: {pdf_path}")
            
            file_path = Path(pdf_path)
            file_size = file_path.stat().st_size
            metadata = self.extract_metadata(pdf_path)
            
            text = ""
            page_count = 0
            extraction_method = method
            
            if method == 'auto':
                # 自动选择最佳提取方法
                try:
                    text, page_count = self._extract_with_pdfplumber(pdf_path)
                    extraction_method = 'pdfplumber'
                    
                    # 如果pdfplumber提取的文本太少，尝试PyPDF2
                    if len(text.strip()) < 100:
                        text2, page_count2 = self._extract_with_pypdf2(pdf_path)
                        if len(text2.strip()) > len(text.strip()):
                            text, page_count = text2, page_count2
                            extraction_method = 'pypdf2'
                            
                except Exception:
                    # pdfplumber失败，使用PyPDF2
                    text, page_count = self._extract_with_pypdf2(pdf_path)
                    extraction_method = 'pypdf2'
                    
            elif method == 'pypdf2':
                text, page_count = self._extract_with_pypdf2(pdf_path)
                
            elif method == 'pdfplumber':
                text, page_count = self._extract_with_pdfplumber(pdf_path)
                
            else:
                raise PDFProcessorError(f"不支持的提取方法: {method}")
            
            # 清理文本
            cleaned_text = self._clean_text(text)
            
            if not cleaned_text:
                logger.warning(f"PDF文档没有提取到文本内容: {pdf_path}")
            
            return DocumentContent(
                content=cleaned_text,
                metadata=metadata,
                page_count=page_count,
                extraction_method=extraction_method,
                file_size=file_size,
                processed_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"PDF文本提取失败 {pdf_path}: {str(e)}")
            raise PDFProcessorError(f"PDF处理失败: {str(e)}")
    
    async def batch_extract_text(self, pdf_paths: List[str]) -> List[DocumentContent]:
        """批量提取PDF文本"""
        results = []
        
        for pdf_path in pdf_paths:
            try:
                result = await self.extract_text(pdf_path)
                results.append(result)
                logger.info(f"PDF处理成功: {pdf_path} ({result.page_count}页)")
                
            except Exception as e:
                logger.error(f"PDF处理失败: {pdf_path} - {str(e)}")
                # 可以选择跳过失败的文档或者添加错误标记
                continue
                
        return results