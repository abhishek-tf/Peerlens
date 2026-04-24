import json
import os
from typing import Dict, Any, Optional
from groq import AsyncGroq  # Updated to Async
from models import PaperInput
 
class LLMAssessor:
    def __init__(self, groq_api_key: str):
        # Initialize the async client
        self.groq_client = AsyncGroq(api_key=groq_api_key)
        print("✅ Async Groq client initialized")
 
    async def comprehensive_assessment(self, 
                                paper: PaperInput,
                                pre_extracted_components: Optional[Dict[str, Any]] = None,
                                assessment_mode: str = "comprehensive") -> Dict[str, Any]:
        """
        Single Async LLM call that does everything:
        - Domain classification
        - Component extraction (if needed)
        - Quality assessment
        - Recommendations
        """
        prompt = self._create_comprehensive_prompt(
            paper, pre_extracted_components, assessment_mode
        )
        
        return await self._assess_with_groq(prompt)
 
    def _create_comprehensive_prompt(self, 
                                   paper: PaperInput,
                                   pre_extracted_components: Optional[Dict[str, Any]],
                                   assessment_mode: str) -> str:
        """
        Create a single comprehensive prompt that handles everything
        """
        # Base prompt
        prompt = f"""You are an expert research methodology reviewer. Perform a comprehensive analysis of this research paper.
 
**Paper Content:**
Title: {paper.title}
Abstract: {paper.abstract}
Methodology: {paper.methodology}
Results: {paper.results or 'Not provided'}
Conclusion: {paper.conclusion or 'Not provided'}
 
"""
        # Add pre-extracted components if available
        if pre_extracted_components:
            prompt += f"""
**Pre-extracted Components (use as reference):**
{json.dumps(pre_extracted_components, indent=2)}
 
Note: Use the pre-extracted components as a starting point, but feel free to add insights or corrections.
"""
        # Assessment instructions based on mode
        if assessment_mode == "comprehensive":
            assessment_instructions = """
**Comprehensive Assessment Required:**
 
1. **CLASSIFICATION**:
   - Research Domain (Computer Science, Medical, Business, Social Sciences, Engineering, Natural Sciences, Other)
   - Study Type (Experimental, System Development, Survey, Case Study, Comparative, Other)
   - Confidence levels for both classifications (0.0-1.0)
 
2. **COMPONENT EXTRACTION** (if not pre-provided or to enhance):
   - Sample information (size, demographics, recruitment)
   - Tools and technologies (with versions if mentioned)
   - Evaluation metrics and measures
   - Statistical methods and tests
   - Study design characteristics
   - Data collection procedures
 
3. **REPRODUCIBILITY ASSESSMENT** (0-100 each):
   - Clarity: Are steps clear and unambiguous?
   - Completeness: All necessary details provided?
   - Resource Availability: Code, data, tools accessible?
   - Replicability: Can others follow the exact process?
 
4. **METHODOLOGICAL RIGOR ASSESSMENT** (0-100 each):
   - Study Design: Appropriate for research questions?
   - Sample Adequacy: Sufficient size and representativeness?
   - Evaluation Validity: Appropriate metrics and comparisons?
   - Statistical Rigor: Proper analysis and significance testing?
 
5. **OVERALL ASSESSMENT**:
   - Key strengths (3-5 points)
   - Critical weaknesses (3-5 points)
   - Actionable recommendations (3-5 specific suggestions)
   - Overall quality rating (Excellent/Good/Fair/Poor)
   - Confidence level in assessment (0.0-1.0)
"""
        elif assessment_mode == "quick":
            assessment_instructions = """
**Quick Assessment Required:**
Focus on key metrics only:
- Domain and study type classification
- Overall reproducibility score (0-100)
- Overall methodological rigor score (0-100)
- Top 3 strengths and weaknesses
- Top 3 recommendations
"""
        else:  # focused
            assessment_instructions = """
**Focused Assessment Required:**
Deep dive into specific aspects:
- Detailed reproducibility analysis
- Statistical methodology evaluation
- Sample adequacy assessment
- Resource availability check
"""
        prompt += assessment_instructions
        
        # Output format
        prompt += """
 
**Required JSON Output Format:**
{
    "classification": {
        "domain": "<domain_name>",
        "study_type": "<study_type>",
        "domain_confidence": <0.0-1.0>,
        "study_type_confidence": <0.0-1.0>,
        "reasoning": "<brief explanation>"
    },
    "extracted_components": {
        "sample_info": {
            "sample_size": <number_or_null>,
            "demographics": "<description>",
            "recruitment_method": "<method>"
        },
        "tools_technologies": ["<tool1>", "<tool2>"],
        "evaluation_metrics": ["<metric1>", "<metric2>"],
        "statistical_methods": ["<method1>", "<method2>"],
        "study_design": "<design_type>",
        "data_collection": "<method>",
        "pre_extracted": <true_if_using_pre_extracted_data>
    },
    "reproducibility": {
        "overall_score": <0-100>,
        "clarity_score": <0-100>,
        "completeness_score": <0-100>,
        "resource_availability_score": <0-100>,
        "replicability_score": <0-100>,
        "clarity_feedback": "<specific feedback>",
        "completeness_feedback": "<specific feedback>",
        "resource_availability_feedback": "<specific feedback>",
        "replicability_feedback": "<specific feedback>",
        "clarity_issues": ["<issue1>", "<issue2>"],
        "completeness_issues": ["<issue1>", "<issue2>"],
        "missing_resources": ["<resource1>", "<resource2>"],
        "replicability_issues": ["<issue1>", "<issue2>"],
        "clarity_strengths": ["<strength1>", "<strength2>"],
        "completeness_strengths": ["<strength1>", "<strength2>"],
        "available_resources": ["<resource1>", "<resource2>"],
        "replicability_strengths": ["<strength1>", "<strength2>"]
    },
    "methodological_rigor": {
        "overall_score": <0-100>,
        "study_design_score": <0-100>,
        "sample_adequacy_score": <0-100>,
        "evaluation_validity_score": <0-100>,
        "statistical_rigor_score": <0-100>,
        "study_design_feedback": "<specific feedback>",
        "sample_adequacy_feedback": "<specific feedback>",
        "evaluation_validity_feedback": "<specific feedback>",
        "statistical_rigor_feedback": "<specific feedback>",
        "design_strengths": ["<strength1>", "<strength2>"],
        "design_weaknesses": ["<weakness1>", "<weakness2>"],
        "sample_strengths": ["<strength1>", "<strength2>"],
        "sample_concerns": ["<concern1>", "<concern2>"],
        "evaluation_strengths": ["<strength1>", "<strength2>"],
        "evaluation_issues": ["<issue1>", "<issue2>"],
        "statistical_strengths": ["<strength1>", "<strength2>"],
        "statistical_issues": ["<issue1>", "<issue2>"]
    },
    "overall_assessment": {
        "key_strengths": ["<strength1>", "<strength2>", "<strength3>"],
        "critical_weaknesses": ["<weakness1>", "<weakness2>", "<weakness3>"],
        "actionable_recommendations": ["<rec1>", "<rec2>", "<rec3>"],
        "confidence_level": <0.0-1.0>,
        "overall_quality": "<Excellent|Good|Fair|Poor>",
        "assessment_summary": "<2-3 sentence summary>"
    }
}
 
Provide ONLY the JSON response, no additional text."""
 
        return prompt
 
    async def _assess_with_groq(self, prompt: str) -> Dict[str, Any]:
        """Single Async Groq API call with strict JSON mode"""
        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert research methodology reviewer. Respond only with valid JSON as requested."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=4096,
                top_p=1,
                stream=False,
                stop=None,
                response_format={"type": "json_object"}  # Forces valid JSON output
            )
            
            response_text = chat_completion.choices[0].message.content
            return self._parse_llm_response(response_text)
            
        except Exception as e:
            raise Exception(f"Groq API error: {str(e)}")
 
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate comprehensive LLM response"""
        try:
            response_text = response_text.strip()
            
            # Native JSON mode usually prevents markdown wrappers, but keeping this as a safety net
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_text = response_text[start_idx:end_idx]
            parsed_response = json.loads(json_text)
            
            # Validate comprehensive structure
            required_keys = [
                'classification', 'extracted_components', 
                'reproducibility', 'methodological_rigor', 'overall_assessment'
            ]
            for key in required_keys:
                if key not in parsed_response:
                    raise ValueError(f"Missing required key: {key}")
            
            return parsed_response
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            raise ValueError(f"Response parsing error: {str(e)}")
 
    async def quick_assessment(self, paper: PaperInput) -> Dict[str, Any]:
        """Quick Async assessment for basic metrics"""
        prompt = f"""Quick assessment of this research paper:
 
Title: {paper.title}
Abstract: {paper.abstract}
Methodology: {paper.methodology}
 
Provide quick scores and basic info in JSON format:
 
{{
    "domain": "<domain_name>",
    "study_type": "<study_type>", 
    "reproducibility_score": <0-100>,
    "rigor_score": <0-100>,
    "sample_size": <number_or_null>,
    "key_tools": ["<tool1>", "<tool2>"],
    "main_strengths": ["<strength1>", "<strength2>"],
    "main_weaknesses": ["<weakness1>", "<weakness2>"],
    "quick_recommendations": ["<rec1>", "<rec2>"],
    "overall_quality": "<Excellent|Good|Fair|Poor>"
}}
 
Respond with ONLY the JSON, no additional text."""
        
        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert research reviewer. Respond only with valid JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=4096,
                top_p=1,
                stream=False,
                stop=None,
                response_format={"type": "json_object"}  # Forces valid JSON output
            )
            
            response_text = chat_completion.choices[0].message.content
            return self._parse_llm_response(response_text)
            
        except Exception as e:
            raise Exception(f"Groq API error: {str(e)}")
 
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate comprehensive LLM response"""
        try:
            response_text = response_text.strip()
            
            # Native JSON mode usually prevents markdown wrappers, but keeping this as a safety net
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_text = response_text[start_idx:end_idx]
            parsed_response = json.loads(json_text)
            
            # Validate comprehensive structure
            required_keys = [
                'classification', 'extracted_components', 
                'reproducibility', 'methodological_rigor', 'overall_assessment'
            ]
            for key in required_keys:
                if key not in parsed_response:
                    raise ValueError(f"Missing required key: {key}")
            
            return parsed_response
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            raise ValueError(f"Response parsing error: {str(e)}")
 
    async def quick_assessment(self, paper: PaperInput) -> Dict[str, Any]:
        """Quick Async assessment for basic metrics"""
        prompt = f"""Quick assessment of this research paper:
 
Title: {paper.title}
Abstract: {paper.abstract}
Methodology: {paper.methodology}
 
Provide quick scores and basic info in JSON format:
 
{{
    "domain": "<domain_name>",
    "study_type": "<study_type>", 
    "reproducibility_score": <0-100>,
    "rigor_score": <0-100>,
    "sample_size": <number_or_null>,
    "key_tools": ["<tool1>", "<tool2>"],
    "main_strengths": ["<strength1>", "<strength2>"],
    "main_weaknesses": ["<weakness1>", "<weakness2>"],
    "quick_recommendations": ["<rec1>", "<rec2>"],
    "overall_quality": "<Excellent|Good|Fair|Poor>"
}}
 
Respond with ONLY the JSON, no additional text."""
        
        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert research reviewer. Respond only with valid JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=1024,
                top_p=1,
                stream=False,
                stop=None,
                response_format={"type": "json_object"} # Forces valid JSON output
            )
            
            response_text = chat_completion.choices[0].message.content
            
            # Reusing the existing parser logic for cleanliness
            parsed_response = json.loads(response_text)
            
            # Validate basic structure for quick assessment
            required_keys = ['domain', 'study_type', 'reproducibility_score', 'rigor_score']
            for key in required_keys:
                if key not in parsed_response:
                    raise ValueError(f"Missing required key in quick assessment: {key}")
            
            return parsed_response
            
        except Exception as e:
            raise Exception(f"Quick assessment failed: {str(e)}")
 
 