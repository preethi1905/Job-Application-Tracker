import re
from typing import Dict, List, Set, Tuple
from app.schemas.matching import (
    CategoryScore,
    MatchResponse,
    MatchSuggestion,
)

# Comprehensive Taxonomy of Technical Skills and Industry Competencies
SKILL_TAXONOMY: Dict[str, List[str]] = {
    "Programming Languages": [
        "python", "javascript", "typescript", "java", "c++", "c#", "golang", "go",
        "ruby", "php", "swift", "kotlin", "rust", "sql", "html", "css", "r", "scala",
    ],
    "Frameworks & Libraries": [
        "fastapi", "flask", "django", "express", "express.js", "react", "react.js",
        "next.js", "vue", "angular", "node.js", "spring", "spring boot", "nestjs",
        "asp.net", "tailwind", "bootstrap", "pandas", "numpy", "sqlalchemy",
    ],
    "Databases & Storage": [
        "postgresql", "postgres", "mysql", "mongodb", "redis", "sqlite",
        "cassandra", "dynamodb", "elasticsearch", "oracle", "bigquery", "snowflake",
    ],
    "Cloud & DevOps": [
        "docker", "kubernetes", "aws", "gcp", "azure", "render", "heroku",
        "github actions", "gitlab ci", "terraform", "ci/cd", "linux", "nginx",
        "cloud run", "ec2", "s3",
    ],
    "API & Architecture": [
        "rest", "rest api", "restful", "rest apis", "graphql", "grpc",
        "microservices", "jwt", "oauth2", "pydantic", "alembic", "orm",
        "event-driven", "websockets", "kafka", "rabbitmq",
    ],
    "Testing & Quality": [
        "pytest", "unittest", "jest", "mocha", "cypress", "unit testing",
        "integration testing", "tdd", "swagger", "openapi", "postman",
    ],
    "AI, ML & NLP": [
        "machine learning", "deep learning", "nlp", "natural language processing",
        "openai", "llm", "prompt engineering", "tf-idf", "pytorch", "tensorflow",
        "scikit-learn", "hugging face", "vector search", "langchain",
    ],
    "Developer Tools & Practices": [
        "git", "github", "gitlab", "jira", "agile", "scrum", "sdlc",
        "ci/cd pipelines", "system design", "code review",
    ],
}

POWER_ACTION_VERBS = [
    "spearheaded", "architected", "engineered", "orchestrated", "accelerated",
    "designed", "developed", "optimized", "implemented", "deployed",
    "automated", "streamlined", "scaled", "refactored", "championed",
]


def normalize_text(text: str) -> str:
    """Normalize text for consistent keyword tokenization."""
    if not text:
        return ""
    # Lowercase and replace non-alphanumeric (except +, #, -, .) with spaces
    text = text.lower()
    text = re.sub(r"[^\w\s\+\#\-\.]", " ", text)
    return text


def extract_skills_from_text(text: str) -> Dict[str, Set[str]]:
    """Scan text against known taxonomies and extract present skills by category."""
    normalized = normalize_text(text)
    words = set(re.findall(r"\b[a-z0-9\+\#\-\.]+\b", normalized))
    
    extracted: Dict[str, Set[str]] = {}
    for category, skill_list in SKILL_TAXONOMY.items():
        found = set()
        for skill in skill_list:
            skill_lower = skill.lower()
            if " " in skill_lower or "." in skill_lower or "-" in skill_lower or "+" in skill_lower or "#" in skill_lower:
                # Multi-word or special token: check regex boundary
                pattern = r"(?:^|\W)" + re.escape(skill_lower) + r"(?:$|\W)"
                if re.search(pattern, normalized):
                    found.add(skill)
            else:
                if skill_lower in words:
                    found.add(skill)
        if found:
            extracted[category] = found
    return extracted


def extract_all_keywords(text: str) -> Set[str]:
    """Extract flattened unique list of skills found in text."""
    cat_skills = extract_skills_from_text(text)
    all_kws = set()
    for skills in cat_skills.values():
        all_kws.update(skills)
    return all_kws


def compute_resume_match(
    application_id: int,
    job_title: str,
    job_description: str,
    resume_text: str,
) -> MatchResponse:
    """
    Ported and enhanced from AI Smart Resume Builder:
    Evaluates resume against job description, returning a match score,
    keyword overlap, missing critical skills, and actionable recommendations.
    """
    if not job_description or not job_description.strip():
        job_description = f"{job_title} role requiring engineering, development, testing and deployment."
    
    if not resume_text or not resume_text.strip():
        resume_text = ""

    jd_by_category = extract_skills_from_text(job_description)
    resume_by_category = extract_skills_from_text(resume_text)

    all_jd_keywords = set()
    for s in jd_by_category.values():
        all_jd_keywords.update(s)

    # If the JD has few catalog keywords, extract general significant terms
    if len(all_jd_keywords) < 3:
        words = re.findall(r"\b[a-z]{4,}\b", normalize_text(job_description))
        common_stops = {
            "with", "that", "this", "from", "have", "will", "your", "team",
            "work", "role", "years", "must", "good", "plus", "ability", "about",
            "experience", "responsibilities", "requirements", "candidate",
        }
        fallback_keywords = {w for w in words if w not in common_stops}
        all_jd_keywords.update(list(fallback_keywords)[:8])

    all_resume_keywords = set()
    for s in resume_by_category.values():
        all_resume_keywords.update(s)

    matched_keywords = sorted(list(all_jd_keywords.intersection(all_resume_keywords)))
    missing_keywords = sorted(list(all_jd_keywords.difference(all_resume_keywords)))

    # Compute category scores
    category_scores: List[CategoryScore] = []
    categories = sorted(list(set(list(jd_by_category.keys()) + list(resume_by_category.keys()))))
    
    category_score_sum = 0.0
    category_count = 0

    for cat in categories:
        jd_skills = jd_by_category.get(cat, set())
        resume_skills = resume_by_category.get(cat, set())
        
        cat_matched = sorted(list(jd_skills.intersection(resume_skills)))
        cat_missing = sorted(list(jd_skills.difference(resume_skills)))
        
        if jd_skills:
            cat_score = round((len(cat_matched) / len(jd_skills)) * 100, 1)
            category_score_sum += cat_score
            category_count += 1
        else:
            cat_score = 100.0 if cat_matched else 0.0

        category_scores.append(
            CategoryScore(
                category=cat,
                matched=cat_matched,
                missing=cat_missing,
                score=cat_score,
            )
        )

    # Overall match calculation
    total_jd = len(all_jd_keywords)
    keyword_ratio = (len(matched_keywords) / total_jd) if total_jd > 0 else 0.0
    
    avg_cat_score = (category_score_sum / category_count) if category_count > 0 else 0.0
    
    # Check for quantitative impact and action verbs in resume
    has_metrics = bool(re.search(r"\d+%|\$\d+|\b\d+\b", resume_text))
    resume_lower = resume_text.lower()
    action_verb_count = sum(1 for verb in POWER_ACTION_VERBS if verb in resume_lower)
    
    quality_bonus = 0.0
    if has_metrics:
        quality_bonus += 5.0
    if action_verb_count >= 3:
        quality_bonus += 5.0

    raw_score = (keyword_ratio * 70.0) + (avg_cat_score * 0.20) + quality_bonus
    match_score = min(100.0, max(0.0, round(raw_score, 1)))

    if match_score >= 80:
        rating = "Strong Match (ATS Ready)"
        summary = "Your resume closely aligns with the JD's core competencies and technical prerequisites."
    elif match_score >= 60:
        rating = "Good Match (Competitive)"
        summary = "Solid overlap in required skills, with minor keyword gaps that can be easily addressed."
    elif match_score >= 40:
        rating = "Moderate Match (Needs Tailoring)"
        summary = "Foundational qualifications exist, but key domain tools and technical keywords are missing."
    else:
        rating = "Needs Significant Tailoring"
        summary = "Significant gap between required job skills and current resume representation."

    # Construct actionable suggestions
    suggestions: List[MatchSuggestion] = []
    
    if missing_keywords:
        top_missing = missing_keywords[:5]
        suggestions.append(
            MatchSuggestion(
                type="missing_critical_skill",
                severity="high" if len(missing_keywords) > 3 else "medium",
                message=f"Missing key JD keywords: {', '.join(top_missing)}.",
                actionable_tip=(
                    f"Integrate keywords like '{top_missing[0]}' into your project descriptions "
                    f"or skills section using the Google XYZ formula: 'Accomplished [X] using {top_missing[0]}, "
                    f"as measured by [Y], by doing [Z]'."
                ),
            )
        )

    if not has_metrics:
        suggestions.append(
            MatchSuggestion(
                type="quantifiable_metrics",
                severity="medium",
                message="No quantified metrics detected in resume text.",
                actionable_tip="Add percentages, throughput numbers, cost savings, or user counts (e.g. 'reduced latency by 35%').",
            )
        )

    if action_verb_count < 3:
        suggestions.append(
            MatchSuggestion(
                type="action_verbs",
                severity="low",
                message="Boost bullet punchiness with executive action verbs.",
                actionable_tip="Start experience bullet points with verbs such as Spearheaded, Engineered, Architected, or Orchestrated.",
            )
        )

    return MatchResponse(
        application_id=application_id,
        job_title=job_title,
        match_score=match_score,
        rating=rating,
        summary=summary,
        total_jd_keywords=total_jd,
        matched_keywords_count=len(matched_keywords),
        missing_keywords_count=len(missing_keywords),
        matching_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        category_scores=category_scores,
        suggestions=suggestions,
        engine="Heuristic-NLP-Matcher (from AI Smart Resume Builder)",
    )
