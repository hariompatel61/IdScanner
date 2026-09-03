from typing import Dict, Optional, List, Type, Any

class DocumentRegistry:
    _plugins: Dict[str, Any] = {}
    _aliases: Dict[str, str] = {}
    
    @classmethod
    def register(cls, plugin: Any):
        cls._plugins[plugin.document_id] = plugin
        for alias in plugin.aliases:
            cls._aliases[alias] = plugin.document_id
            
    @classmethod
    def get(cls, document_id: str) -> Optional[Any]:
        if not document_id: return None
        real_id = cls._aliases.get(document_id.lower(), document_id.lower())
        return cls._plugins.get(real_id)
        
    @classmethod
    def list_documents(cls) -> List[str]:
        return list(cls._plugins.keys())
        
    @classmethod
    def supports(cls, document_id: str) -> bool:
        return cls.get(document_id) is not None
        
document_registry = DocumentRegistry()
