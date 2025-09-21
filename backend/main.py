from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import re
import hashlib
import datetime
from enum import Enum
import asyncio
import aiohttp
import base64

# Initialize FastAPI app
app = FastAPI(
    title="TruthGuard AI - Misinformation Detection API",
    description="AI-powered misinformation detection and explanation tool for India",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class ContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"

class Language(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    TELUGU = "te"
    BENGALI = "bn"
    TAMIL = "ta"
    HINGLISH = "hi-en"

class TrustLevel(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    MISLEADING = "MISLEADING"
    UNVERIFIED = "UNVERIFIED"
    SATIRE = "SATIRE"

class Claim(BaseModel):
    claim_text: str
    trust_level: TrustLevel
    confidence: float
    explanation: str
    sources: List[str]
    manipulation_techniques: List[str] = []

class CheckRequest(BaseModel):
    content: str
    content_type: ContentType = ContentType.TEXT
    language: Language = Language.ENGLISH
    include_education: bool = True

class CheckResponse(BaseModel):
    overall_trust_score: float
    overall_verdict: TrustLevel
    claims: List[Claim]
    explanation: str
    sources: List[str]
    educational_insights: Optional[Dict[str, Any]] = None
    processing_time: float
    content_hash: str

# Mock databases for demonstration
FACT_DATABASE = {
    # Health misinformation
    "microchip": {
        "verdict": TrustLevel.FALSE,
        "confidence": 98,
        "explanation": "COVID-19 vaccines do not contain microchips. This has been thoroughly debunked by health organizations worldwide.",
        "sources": ["WHO", "CDC", "Reuters Fact Check", "PIB Fact Check"],
        "techniques": ["Fear Mongering", "Conspiracy Theory"]
    },
    "5g coronavirus": {
        "verdict": TrustLevel.FALSE,
        "confidence": 95,
        "explanation": "There is no scientific evidence linking 5G networks to COVID-19. Viruses cannot spread through radio waves.",
        "sources": ["WHO", "ICMR", "IEEE", "Nature Journal"],
        "techniques": ["False Causation", "Technology Fear"]
    },
    
    # Political misinformation patterns
    "election fraud": {
        "verdict": TrustLevel.MISLEADING,
        "confidence": 75,
        "explanation": "Claims of widespread election fraud require verification from official sources and election commissions.",
        "sources": ["Election Commission of India", "Supreme Court", "Press Trust of India"],
        "techniques": ["Unsubstantiated Claims", "Cherry Picking"]
    },
    
    # Economic misinformation
    "demonetization complete failure": {
        "verdict": TrustLevel.MISLEADING,
        "confidence": 65,
        "explanation": "Demonetization had mixed results. Economic assessments vary and should be evaluated based on comprehensive data.",
        "sources": ["Reserve Bank of India", "Ministry of Finance", "Economic Survey"],
        "techniques": ["Oversimplification", "Selective Reporting"]
    },
    
    # Social misinformation
    "beef ban nationwide": {
        "verdict": TrustLevel.MISLEADING,
        "confidence": 80,
        "explanation": "Beef regulations vary by state in India. No uniform nationwide ban exists.",
        "sources": ["Supreme Court of India", "Ministry of Home Affairs", "State Government Notifications"],
        "techniques": ["Generalization", "Context Manipulation"]
    }
}

EDUCATIONAL_CONTENT = {
    "manipulation_techniques": {
        "Fear Mongering": {
            "description": "Using fear to influence opinion without factual basis",
            "example": "Claiming vaccines are dangerous without scientific evidence",
            "detection_tips": ["Look for emotional language", "Check for scientific sources", "Verify with health authorities"]
        },
        "False Causation": {
            "description": "Claiming one thing causes another without evidence",
            "example": "Saying 5G causes COVID-19",
            "detection_tips": ["Look for 'correlation vs causation'", "Check for scientific studies", "Consult expert opinions"]
        },
        "Cherry Picking": {
            "description": "Selecting only facts that support a particular viewpoint",
            "example": "Using only negative statistics while ignoring positive ones",
            "detection_tips": ["Look for complete context", "Check multiple sources", "Verify data completeness"]
        },
        "Context Manipulation": {
            "description": "Taking real information and presenting it in wrong context",
            "example": "Using old photos for current news",
            "detection_tips": ["Reverse image search", "Check publication dates", "Verify original context"]
        }
    },
    "source_verification": {
        "trusted_indian_sources": [
            "Press Information Bureau (PIB)",
            "Press Trust of India (PTI)",
            "Indian Council of Medical Research (ICMR)",
            "Election Commission of India",
            "Reserve Bank of India (RBI)",
            "Ministry of Health and Family Welfare"
        ],
        "fact_checking_sites": [
            "PIB Fact Check",
            "Vishvas News",
            "Boom Live",
            "Alt News",
            "India Today Fact Check",
            "Factly"
        ]
    }
}

# Language detection and translation simulation
def detect_language(text: str) -> Language:
    """Simulate language detection"""
    hindi_keywords = ['है', 'का', 'में', 'से', 'को', 'और', 'नहीं', 'यह', 'वह', 'के']
    telugu_keywords = ['అని', 'లో', 'కు', 'వి', 'తో', 'గా', 'చే', 'లేదా', 'కాని']
    bengali_keywords = ['এর', 'তার', 'যে', 'এই', 'সে', 'আর', 'না', 'করে', 'হয়']
    tamil_keywords = ['அது', 'இது', 'என்று', 'மற்றும்', 'அல்லது', 'ஆக', 'இல்லை']
    
    text_lower = text.lower()
    
    if any(keyword in text for keyword in hindi_keywords):
        return Language.HINDI
    elif any(keyword in text for keyword in telugu_keywords):
        return Language.TELUGU
    elif any(keyword in text for keyword in bengali_keywords):
        return Language.BENGALI
    elif any(keyword in text for keyword in tamil_keywords):
        return Language.TAMIL
    elif re.search(r'[a-zA-Z]', text) and any(keyword in text for keyword in hindi_keywords):
        return Language.HINGLISH
    else:
        return Language.ENGLISH

# Enhanced claim extraction
def extract_claims(content: str, language: Language) -> List[str]:
    """Extract factual claims from content"""
    # Patterns for claim detection
    claim_patterns = [
        r'vaccines?\s+contain\s+\w+',
        r'\d+g?\s+(?:causes?|leads? to|results? in)\s+\w+',
        r'government\s+(?:bans?|allows?|announces?)\s+\w+',
        r'studies?\s+(?:shows?|proves?|confirms?)\s+\w+',
        r'experts?\s+(?:says?|claims?|warns?)\s+\w+',
        r'research\s+(?:indicates?|suggests?|reveals?)\s+\w+'
    ]
    
    claims = []
    content_lower = content.lower()
    
    # Extract sentences that might contain claims
    sentences = re.split(r'[.!?]+', content)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 20:  # Filter out very short sentences
            # Check if sentence contains claim patterns
            for pattern in claim_patterns:
                if re.search(pattern, sentence.lower()):
                    claims.append(sentence)
                    break
    
    # If no pattern-based claims found, extract key sentences
    if not claims:
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
        claims = sentences[:3]  # Take first 3 meaningful sentences
    
    return claims[:5]  # Limit to 5 claims max

# Enhanced fact verification
def verify_claim(claim_text: str) -> Claim:
    """Verify a single claim against fact database"""
    claim_lower = claim_text.lower()
    
    # Check against known patterns in fact database
    for pattern, fact_info in FACT_DATABASE.items():
        if pattern in claim_lower:
            return Claim(
                claim_text=claim_text,
                trust_level=fact_info["verdict"],
                confidence=fact_info["confidence"],
                explanation=fact_info["explanation"],
                sources=fact_info["sources"],
                manipulation_techniques=fact_info.get("techniques", [])
            )
    
    # Default response for unknown claims
    return Claim(
        claim_text=claim_text,
        trust_level=TrustLevel.UNVERIFIED,
        confidence=50.0,
        explanation="This claim could not be verified against our current database. Please check with reliable sources.",
        sources=["Manual verification required"],
        manipulation_techniques=[]
    )

# Calculate overall trust score
def calculate_trust_score(claims: List[Claim]) -> tuple[float, TrustLevel]:
    """Calculate overall trust score and verdict"""
    if not claims:
        return 50.0, TrustLevel.UNVERIFIED
    
    score_mapping = {
        TrustLevel.TRUE: 90,
        TrustLevel.MISLEADING: 40,
        TrustLevel.FALSE: 10,
        TrustLevel.UNVERIFIED: 50,
        TrustLevel.SATIRE: 70
    }
    
    total_score = sum(score_mapping[claim.trust_level] * claim.confidence / 100 for claim in claims)
    average_score = total_score / len(claims)
    
    # Determine overall verdict
    if average_score >= 80:
        verdict = TrustLevel.TRUE
    elif average_score >= 60:
        verdict = TrustLevel.UNVERIFIED
    elif average_score >= 30:
        verdict = TrustLevel.MISLEADING
    else:
        verdict = TrustLevel.FALSE
    
    return round(average_score, 1), verdict

# Generate educational insights
def generate_educational_insights(claims: List[Claim]) -> Dict[str, Any]:
    """Generate educational content based on claims"""
    techniques_found = []
    for claim in claims:
        techniques_found.extend(claim.manipulation_techniques)
    
    unique_techniques = list(set(techniques_found))
    
    insights = {
        "manipulation_techniques_detected": unique_techniques,
        "technique_explanations": {
            tech: EDUCATIONAL_CONTENT["manipulation_techniques"].get(tech, {})
            for tech in unique_techniques
        },
        "verification_tips": [
            "Cross-check with multiple reliable sources",
            "Look for original sources and citations",
            "Check the publication date and context",
            "Verify images with reverse image search",
            "Be skeptical of highly emotional content"
        ],
        "trusted_sources": EDUCATIONAL_CONTENT["source_verification"]["trusted_indian_sources"][:5],
        "fact_check_resources": EDUCATIONAL_CONTENT["source_verification"]["fact_checking_sites"][:3]
    }
    
    return insights

# Main API endpoints
@app.get("/")
async def root():
    return {
        "message": "TruthGuard AI - Misinformation Detection API",
        "version": "1.0.0",
        "status": "active",
        "supported_languages": [lang.value for lang in Language],
        "supported_content_types": [ct.value for ct in ContentType]
    }

@app.post("/check", response_model=CheckResponse)
async def check_misinformation(request: CheckRequest):
    """Main endpoint for misinformation detection"""
    start_time = datetime.datetime.now()
    
    try:
        # Detect language if not specified
        detected_language = detect_language(request.content)
        if request.language == Language.ENGLISH and detected_language != Language.ENGLISH:
            request.language = detected_language
        
        # Extract claims from content
        claim_texts = extract_claims(request.content, request.language)
        
        # Verify each claim
        verified_claims = [verify_claim(claim_text) for claim_text in claim_texts]
        
        # Calculate overall trust score
        trust_score, verdict = calculate_trust_score(verified_claims)
        
        # Generate explanation
        explanation = f"Based on analysis of {len(verified_claims)} claims, this content has a trust score of {trust_score}%. "
        if verdict == TrustLevel.FALSE:
            explanation += "This content contains significant misinformation and should not be trusted."
        elif verdict == TrustLevel.MISLEADING:
            explanation += "This content contains some misleading information. Verify with reliable sources."
        elif verdict == TrustLevel.TRUE:
            explanation += "This content appears to be largely accurate based on available information."
        else:
            explanation += "This content requires further verification from reliable sources."
        
        # Collect all sources
        all_sources = list(set([source for claim in verified_claims for source in claim.sources]))
        
        # Generate educational insights
        educational_insights = None
        if request.include_education:
            educational_insights = generate_educational_insights(verified_claims)
        
        # Calculate processing time
        end_time = datetime.datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Generate content hash for caching
        content_hash = hashlib.md5(request.content.encode()).hexdigest()
        
        return CheckResponse(
            overall_trust_score=trust_score,
            overall_verdict=verdict,
            claims=verified_claims,
            explanation=explanation,
            sources=all_sources,
            educational_insights=educational_insights,
            processing_time=round(processing_time, 3),
            content_hash=content_hash
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.post("/check-image")
async def check_image_content(file: UploadFile = File(...)):
    """Endpoint for image-based misinformation detection"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Simulate OCR and image analysis
    # In production, integrate with Google Vision API or similar
    mock_extracted_text = "Sample text extracted from image: This is a demonstration of image content analysis."
    
    request = CheckRequest(
        content=mock_extracted_text,
        content_type=ContentType.IMAGE,
        include_education=True
    )
    
    return await check_misinformation(request)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "database_status": "active",
        "fact_database_entries": len(FACT_DATABASE)
    }

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    return {
        "total_fact_patterns": len(FACT_DATABASE),
        "supported_languages": len(Language),
        "educational_techniques": len(EDUCATIONAL_CONTENT["manipulation_techniques"]),
        "trusted_sources": len(EDUCATIONAL_CONTENT["source_verification"]["trusted_indian_sources"]),
        "fact_check_resources": len(EDUCATIONAL_CONTENT["source_verification"]["fact_checking_sites"])
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
