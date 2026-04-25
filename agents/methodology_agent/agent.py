import os
import logging
import asyncio
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
 
from models import (
    PaperInput, AssessmentResult, ResearchDomain, StudyType,
    ComponentScore, ReproducibilityAssessment, MethodologicalRigor
)
from llm_assessor import LLMAssessor
 
# Setup professional logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
load_dotenv()
 
class StreamlinedMethodologyAssessmentAgent:
    def __init__(self, 
                 groq_api_key: Optional[str] = None,
                 use_llm: bool = True):
        
        self.use_llm = use_llm
        self.llm_assessor = None
        
        if use_llm:
            groq_key = groq_api_key or os.getenv('GROQ_API_KEY')
            if groq_key:
                try:
                    self.llm_assessor = LLMAssessor(groq_key)
                    logger.info("🤖 LLM-First mode: Intelligent assessment enabled")
                except Exception as e:
                    logger.error(f"⚠️  LLM initialization failed: {e}")
                    logger.warning("📋 Falling back to rule-based assessment")
                    self.use_llm = False
            else:
                logger.warning("📋 No API key provided, using rule-based assessment")
                self.use_llm = False
        else:
            logger.info("📋 Rule-based assessment mode")
    
    async def assess(self, 
               paper: PaperInput, 
               pre_extracted_components: Optional[Dict[str, Any]] = None,
               assessment_mode: str = "comprehensive") -> AssessmentResult:
        logger.info(f"🔍 Analyzing: {paper.title[:50]}...")
        
        if self.use_llm and self.llm_assessor:
            try:
                return await self._llm_comprehensive_assessment(
                    paper, pre_extracted_components, assessment_mode
                )
            except Exception as e:
                logger.error(f"❌ LLM assessment failed: {e}")
                return self._rule_based_fallback(paper, pre_extracted_components)
        else:
            return self._rule_based_fallback(paper, pre_extracted_components)
    
    async def _llm_comprehensive_assessment(self, 
                                    paper: PaperInput,
                                    pre_extracted_components: Optional[Dict[str, Any]],
                                    assessment_mode: str) -> AssessmentResult:
        llm_result = await self.llm_assessor.comprehensive_assessment(
            paper=paper,
            pre_extracted_components=pre_extracted_components,
            assessment_mode=assessment_mode
        )
        return self._convert_llm_to_assessment_result(llm_result, paper)
    
    def _rule_based_fallback(self, 
                           paper: PaperInput,
                           pre_extracted_components: Optional[Dict[str, Any]]) -> AssessmentResult:
        logger.warning("📋 Using minimal rule-based backup assessment...")
        
        methodology_words = len(paper.methodology.split()) if paper.methodology else 0
        has_results = bool(paper.results and len(paper.results.strip()) > 50)
        
        base_score = 30
        if methodology_words > 100: base_score += 10
        if has_results: base_score += 10
        
        repro_score = min(60, base_score)
        rigor_score = min(55, base_score - 5)
        
        # Recommendations logic for fallback
        fallback_recommendations = []
        if methodology_words < 100:
            fallback_recommendations.append("Provide more detailed methodology description")
        if not has_results:
            fallback_recommendations.append("Include comprehensive results section")
            
        if not fallback_recommendations:
            fallback_recommendations = ["Consider LLM-based assessment for detailed analysis"]
        
        reproducibility = ReproducibilityAssessment(
            overall_score=repro_score,
            clarity=ComponentScore(score=repro_score, feedback="Limited analysis", issues=[], strengths=[]),
            completeness=ComponentScore(score=repro_score, feedback="Limited analysis", issues=[], strengths=[]),
            resource_availability=ComponentScore(score=0, feedback="Not assessed", issues=[], strengths=[]),
            replicability=ComponentScore(score=repro_score, feedback="Limited analysis", issues=[], strengths=[])
        )
        
        methodological_rigor = MethodologicalRigor(
            overall_score=rigor_score,
            study_design=ComponentScore(score=rigor_score, feedback="Limited analysis", issues=[], strengths=[]),
            sample_adequacy=ComponentScore(score=rigor_score, feedback="Limited analysis", issues=[], strengths=[]),
            evaluation_validity=ComponentScore(score=rigor_score, feedback="Limited analysis", issues=[], strengths=[]),
            statistical_rigor=ComponentScore(score=rigor_score, feedback="Limited analysis", issues=[], strengths=[])
        )
        
        return AssessmentResult(
            metadata={"assessment_method": "Rule-based fallback"},
            reproducibility_assessment=reproducibility,
            methodological_rigor=methodological_rigor,
            identified_strengths=["Paper structure present"],
            identified_weaknesses=["Limited rule-based analysis"],
            recommendations=fallback_recommendations,
            confidence_score=0.2
        )
    
    def _convert_llm_to_assessment_result(self, 
                                        llm_result: Dict[str, Any],
                                        paper: PaperInput) -> AssessmentResult:
        """Corrected: Maps dictionary keys from LLM response to AssessmentResult object"""
        repro_data = llm_result['reproducibility']
        rigor_data = llm_result['methodological_rigor']
        overall_data = llm_result['overall_assessment']
        classification_data = llm_result['classification']
        extraction_data = llm_result['extracted_components']
        
        reproducibility = ReproducibilityAssessment(
            overall_score=repro_data['overall_score'],
            clarity=ComponentScore(score=repro_data['clarity_score'], feedback=repro_data['clarity_feedback'], issues=repro_data.get('clarity_issues', []), strengths=repro_data.get('clarity_strengths', [])),
            completeness=ComponentScore(score=repro_data['completeness_score'], feedback=repro_data['completeness_feedback'], issues=repro_data.get('completeness_issues', []), strengths=repro_data.get('completeness_strengths', [])),
            resource_availability=ComponentScore(score=repro_data['resource_availability_score'], feedback=repro_data['resource_availability_feedback'], issues=repro_data.get('missing_resources', []), strengths=repro_data.get('available_resources', [])),
            replicability=ComponentScore(score=repro_data['replicability_score'], feedback=repro_data['replicability_feedback'], issues=repro_data.get('replicability_issues', []), strengths=repro_data.get('replicability_strengths', []))
        )
        
        methodological_rigor = MethodologicalRigor(
            overall_score=rigor_data['overall_score'],
            study_design=ComponentScore(score=rigor_data['study_design_score'], feedback=rigor_data['study_design_feedback'], issues=rigor_data.get('design_weaknesses', []), strengths=rigor_data.get('design_strengths', [])),
            sample_adequacy=ComponentScore(score=rigor_data['sample_adequacy_score'], feedback=rigor_data['sample_adequacy_feedback'], issues=rigor_data.get('sample_concerns', []), strengths=rigor_data.get('sample_strengths', [])),
            evaluation_validity=ComponentScore(score=rigor_data['evaluation_validity_score'], feedback=rigor_data['evaluation_validity_feedback'], issues=rigor_data.get('evaluation_issues', []), strengths=rigor_data.get('evaluation_strengths', [])),
            statistical_rigor=ComponentScore(score=rigor_data['statistical_rigor_score'], feedback=rigor_data['statistical_rigor_feedback'], issues=rigor_data.get('statistical_issues', []), strengths=rigor_data.get('statistical_strengths', []))
        )
        
        return AssessmentResult(
            metadata={
                "classified_domain": classification_data['domain'],
                "study_type": classification_data['study_type'],
                "assessment_method": "LLM Comprehensive",
                "extracted_components": extraction_data
            },
            reproducibility_assessment=reproducibility,
            methodological_rigor=methodological_rigor,
            identified_strengths=overall_data.get('key_strengths', []),
            identified_weaknesses=overall_data.get('critical_weaknesses', []),
            recommendations=overall_data.get('actionable_recommendations', []), # Correctly pulling from dictionary
            confidence_score=overall_data.get('confidence_level', 0.8)
        )
    
    async def quick_assess(self, paper: PaperInput) -> dict:
        """Quick Async assessment - LLM or rule-based"""
        if self.use_llm and self.llm_assessor:
            try:
                return await self.llm_assessor.quick_assessment(paper)
            except Exception as e:
                logger.error(f"❌ Quick LLM assessment failed: {e}")
                return self._quick_rule_based(paper)
        else:
            return self._quick_rule_based(paper)
    
    def _quick_rule_based(self, paper: PaperInput) -> dict:
        """Quick rule-based assessment"""
        methodology_words = len(paper.methodology.split()) if paper.methodology else 0
        has_results = bool(paper.results and len(paper.results.strip()) > 50)
        
        base_score = 30
        if methodology_words > 100: base_score += 15
        if has_results: base_score += 10
        
        return {
            "domain": "Unknown",
            "study_type": "Unknown",
            "reproducibility_score": min(60, base_score),
            "rigor_score": min(55, base_score - 5),
            "sample_size": None,
            "key_tools": [],
            "main_strengths": ["Paper structure present"],
            "main_weaknesses": ["Limited rule-based analysis"],
            "quick_recommendations": ["Use LLM assessment for detailed analysis"],
            "overall_quality": "Fair" if base_score > 40 else "Poor",
            "assessment_method": "Rule-based backup"
        }
    
    async def batch_assess(self, papers: List[PaperInput]) -> List[AssessmentResult]:
        """Batch processing concurrently for multiple papers"""
        logger.info(f"📄 Processing {len(papers)} papers concurrently...")
        
        # Create an async task for each paper
        tasks = [self.assess(paper) for paper in papers]
        
        # Run them all at the exact same time
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Clean up any exceptions that leaked through
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Failed to assess paper {i+1}: {result}")
                final_results.append(self._create_error_result(papers[i], str(result)))
            else:
                final_results.append(result)
                
        return final_results
    
    def _create_error_result(self, paper: PaperInput, error: str) -> AssessmentResult:
        """Create error result for failed assessments"""
        return AssessmentResult(
            metadata={"error": error, "assessment_method": "Failed"},
            reproducibility_assessment=ReproducibilityAssessment(
                overall_score=0,
                clarity=ComponentScore(score=0, feedback=f"Assessment failed: {error}", issues=[], strengths=[]),
                completeness=ComponentScore(score=0, feedback="", issues=[], strengths=[]),
                resource_availability=ComponentScore(score=0, feedback="", issues=[], strengths=[]),
                replicability=ComponentScore(score=0, feedback="", issues=[], strengths=[])
            ),
            methodological_rigor=MethodologicalRigor(
                overall_score=0,
                study_design=ComponentScore(score=0, feedback="", issues=[], strengths=[]),
                sample_adequacy=ComponentScore(score=0, feedback="", issues=[], strengths=[]),
                evaluation_validity=ComponentScore(score=0, feedback="", issues=[], strengths=[]),
                statistical_rigor=ComponentScore(score=0, feedback="", issues=[], strengths=[])
            ),
            identified_strengths=[],
            identified_weaknesses=[f"Assessment failed: {error}"],
            recommendations=["Please retry assessment or check paper format"],
            confidence_score=0.0
        )
