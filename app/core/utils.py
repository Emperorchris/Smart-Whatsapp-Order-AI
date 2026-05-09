import enum

class MessageType(enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    
    

class MessageStatus(enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    
    
class ConversationStatus(enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"
    
    
class ConversationType(enum.Enum):
    ONE_TO_ONE = "one_to_one"
    GROUP = "group"
    CHANNEL = "channel"
    CUSTOMER_SERVICE = "customer_service"
    AI_KNOWLEDGE_BASED = "ai_knowledge_based"
    
    
class MessageDirection(enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    
class CustomerSegment(enum.Enum):
    NEW = "new"
    RETURNING = "returning"
    VIP = "vip"
    CHURNED = "churned"
    

class CustomerStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    
    
class CustomerType(enum.Enum):
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"
    
    
class CartStatus(enum.Enum):
    ACTIVE = "active"
    CHECKED_OUT = "checked_out"
    ABANDONED = "abandoned"
    
    
class OrderStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    
    
class PaymentStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"