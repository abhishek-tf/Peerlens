import os
import logging
import asyncio
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import AsyncGroq

# Setup professional logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class PaperInput(BaseModel):
    title: str
    abstract: str
    methodology: str
    results: Optional[str] = None
    conclusion: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_raw_json(cls, data: Dict[str, Any]):
        sections = data.get("sections", {})
        
        def get_content(primary_key, fallback_list):
            content = data.get(primary_key.lower())
            if content: return content
            for fb in fallback_list:
                content = data.get(fb.lower())
                if content: return content
            section_keys = {k.upper(): v for k, v in sections.items()}
            if primary_key.upper() in section_keys:
                return section_keys[primary_key.upper()]
            for fb in fallback_list:
                if fb.upper() in section_keys:
                    return section_keys[fb.upper()]
            return ""

        return cls(
            title=data.get("title", "Unknown Title"),
            abstract=get_content("abstract", ["intro", "introduction"]),
            methodology=get_content("methodology", ["methods", "materials and methods", "experimental setup"]),
            results=get_content("results", ["findings", "evaluation"]),
            conclusion=get_content("conclusion", ["conclusions", "discussion"]),
            metadata=data.get("metadata", {})
        )

class ComponentScore(BaseModel):
    score: float
    feedback: str
    issues: List[str] = []
    strengths: List[str] = []

class ReproducibilityAssessment(BaseModel):
    overall_score: float
    clarity: ComponentScore
    completeness: ComponentScore
    resource_availability: ComponentScore
    replicability: ComponentScore

class MethodologicalRigor(BaseModel):
    overall_score: float
    study_design: ComponentScore
    sample_adequacy: ComponentScore
    evaluation_validity: ComponentScore
    statistical_rigor: ComponentScore

class AssessmentResult(BaseModel):
    metadata: Dict[str, Any]
    reproducibility_assessment: ReproducibilityAssessment
    methodological_rigor: MethodologicalRigor
    identified_strengths: List[str]
    identified_weaknesses: List[str]
    recommendations: List[str]
    confidence_score: float



class LLMAssessor:
    def __init__(self, groq_api_key: str):
        self.groq_client = AsyncGroq(api_key=groq_api_key)
        logger.info("✅ Async Groq client initialized")

    async def comprehensive_assessment(self, 
                                paper: PaperInput,
                                pre_extracted_components: Optional[Dict[str, Any]] = None,
                                assessment_mode: str = "comprehensive") -> Dict[str, Any]:
        prompt = self._create_comprehensive_prompt(paper, pre_extracted_components, assessment_mode)
        return await self._assess_with_groq(prompt)

    def _create_comprehensive_prompt(self, paper: PaperInput, pre_extracted_components: Optional[Dict[str, Any]], assessment_mode: str) -> str:
        prompt = f"""You are an expert research methodology reviewer. Perform a comprehensive analysis.
Paper Content:
Title: {paper.title}
Abstract: {paper.abstract}
Methodology: {paper.methodology}
Results: {paper.results or 'Not provided'}
Conclusion: {paper.conclusion or 'Not provided'}
"""
        if pre_extracted_components:
            prompt += f"\nPre-extracted Components:\n{json.dumps(pre_extracted_components, indent=2)}\n"

        prompt += """
**Required JSON Output Format:**
{
    "classification": {"domain": "str", "study_type": "str", "reasoning": "str"},
    "extracted_components": {"sample_info": {"sample_size": 0}, "tools_technologies": [], "evaluation_metrics": [], "statistical_methods": []},
    "reproducibility": {
        "overall_score": 0, "clarity_score": 0, "completeness_score": 0, "resource_availability_score": 0, "replicability_score": 0,
        "clarity_feedback": "str", "clarity_issues": [], "clarity_strengths": [],
        "completeness_feedback": "str", "completeness_issues": [], "completeness_strengths": [],
        "resource_availability_feedback": "str", "missing_resources": [], "available_resources": [],
        "replicability_feedback": "str", "replicability_issues": [], "replicability_strengths": []
    },
    "methodological_rigor": {
        "overall_score": 0, "study_design_score": 0, "sample_adequacy_score": 0, "evaluation_validity_score": 0, "statistical_rigor_score": 0,
        "study_design_feedback": "str", "design_strengths": [], "design_weaknesses": [],
        "sample_adequacy_feedback": "str", "sample_strengths": [], "sample_concerns": [],
        "evaluation_validity_feedback": "str", "evaluation_strengths": [], "evaluation_issues": [],
        "statistical_rigor_feedback": "str", "statistical_strengths": [], "statistical_issues": []
    },
    "overall_assessment": {
        "key_strengths": [], "critical_weaknesses": [], "actionable_recommendations": [], "confidence_level": 0.0, "overall_quality": "str"
    }
}
Respond ONLY with JSON."""
        return prompt

    async def _assess_with_groq(self, prompt: str) -> Dict[str, Any]:
        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[{"role": "system", "content": "You are a research reviewer. Return valid JSON."},
                          {"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            return json.loads(chat_completion.choices[0].message.content)
        except Exception as e:
            raise Exception(f"Groq API error: {str(e)}")

    async def quick_assessment(self, paper: PaperInput) -> Dict[str, Any]:
        prompt = f"Quick assessment of {paper.title}. Provide JSON with domain, reproducibility_score, rigor_score."
        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )
            return json.loads(chat_completion.choices[0].message.content)
        except Exception as e:
            raise Exception(f"Quick assessment failed: {str(e)}")


class StreamlinedMethodologyAssessmentAgent:
    def __init__(self, groq_api_key: Optional[str] = None, use_llm: bool = True):
        self.use_llm = use_llm
        self.llm_assessor = None
        
        if use_llm:
            groq_key = groq_api_key or os.getenv('GROQ_API_KEY')
            if groq_key:
                self.llm_assessor = LLMAssessor(groq_key)
                logger.info("🤖 LLM-First mode: Intelligent assessment enabled")
            else:
                logger.warning("📋 No API key, using rule-based assessment")
                self.use_llm = False

    async def assess(self, paper: PaperInput, pre_extracted_components: Optional[Dict[str, Any]] = None, assessment_mode: str = "comprehensive") -> AssessmentResult:
        logger.info(f"🔍 Analyzing: {paper.title[:50]}...")
        if self.use_llm and self.llm_assessor:
            try:
                llm_result = await self.llm_assessor.comprehensive_assessment(paper, pre_extracted_components, assessment_mode)
                return self._convert_llm_to_assessment_result(llm_result, paper)
            except Exception as e:
                logger.error(f"❌ LLM assessment failed: {e}")
                return self._rule_based_fallback(paper)
        return self._rule_based_fallback(paper)

    def _convert_llm_to_assessment_result(self, llm_result: Dict[str, Any], paper: PaperInput) -> AssessmentResult:
        repro = llm_result.get('reproducibility', {})
        rigor = llm_result.get('methodological_rigor', {})
        overall = llm_result.get('overall_assessment', {})
        
        return AssessmentResult(
            metadata={"assessment_method": "LLM Comprehensive", "paper_metadata": paper.metadata},
            reproducibility_assessment=ReproducibilityAssessment(
                overall_score=repro.get('overall_score', 0),
                clarity=ComponentScore(score=repro.get('clarity_score', 0), feedback=repro.get('clarity_feedback', ""), issues=repro.get('clarity_issues', []), strengths=repro.get('clarity_strengths', [])),
                completeness=ComponentScore(score=repro.get('completeness_score', 0), feedback=repro.get('completeness_feedback', ""), issues=repro.get('completeness_issues', []), strengths=repro.get('completeness_strengths', [])),
                resource_availability=ComponentScore(score=repro.get('resource_availability_score', 0), feedback=repro.get('resource_availability_feedback', ""), issues=repro.get('missing_resources', []), strengths=repro.get('available_resources', [])),
                replicability=ComponentScore(score=repro.get('replicability_score', 0), feedback=repro.get('replicability_feedback', ""), issues=repro.get('replicability_issues', []), strengths=repro.get('replicability_strengths', []))
            ),
            methodological_rigor=MethodologicalRigor(
                overall_score=rigor.get('overall_score', 0),
                study_design=ComponentScore(score=rigor.get('study_design_score', 0), feedback=rigor.get('study_design_feedback', ""), issues=rigor.get('design_weaknesses', []), strengths=rigor.get('design_strengths', [])),
                sample_adequacy=ComponentScore(score=rigor.get('sample_adequacy_score', 0), feedback=rigor.get('sample_adequacy_feedback', ""), issues=rigor.get('sample_concerns', []), strengths=rigor.get('sample_strengths', [])),
                evaluation_validity=ComponentScore(score=rigor.get('evaluation_validity_score', 0), feedback=rigor.get('evaluation_validity_feedback', ""), issues=rigor.get('evaluation_issues', []), strengths=rigor.get('evaluation_strengths', [])),
                statistical_rigor=ComponentScore(score=rigor.get('statistical_rigor_score', 0), feedback=rigor.get('statistical_rigor_feedback', ""), issues=rigor.get('statistical_issues', []), strengths=rigor.get('statistical_strengths', []))
            ),
            identified_strengths=overall.get('key_strengths', []),
            identified_weaknesses=overall.get('critical_weaknesses', []),
            recommendations=overall.get('actionable_recommendations', []),
            confidence_score=overall.get('confidence_level', 0.0)
        )

    def _rule_based_fallback(self, paper: PaperInput) -> AssessmentResult:
        logger.warning("📋 Rule-based backup...")
        score = 40 if len(paper.methodology) > 500 else 20
        return AssessmentResult(
            metadata={"assessment_method": "Rule-based fallback"},
            reproducibility_assessment=ReproducibilityAssessment(
                overall_score=score,
                clarity=ComponentScore(score=score, feedback="Fallback"),
                completeness=ComponentScore(score=score, feedback="Fallback"),
                resource_availability=ComponentScore(score=0, feedback="N/A"),
                replicability=ComponentScore(score=score, feedback="Fallback")
            ),
            methodological_rigor=MethodologicalRigor(
                overall_score=score-5,
                study_design=ComponentScore(score=score-5, feedback="Fallback"),
                sample_adequacy=ComponentScore(score=score-5, feedback="Fallback"),
                evaluation_validity=ComponentScore(score=score-5, feedback="Fallback"),
                statistical_rigor=ComponentScore(score=score-5, feedback="Fallback")
            ),
            identified_strengths=["Structure present"],
            identified_weaknesses=["Limited analysis"],
            recommendations=["Check API configuration"],
            confidence_score=0.1
        )