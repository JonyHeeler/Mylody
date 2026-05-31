"""回归测试集：典型歌曲测试用例"""

TEST_CASES = [
    {
        "name": "热门英文歌曲",
        "track": {"title": "Counting Stars", "artist": "OneRepublic", "album": "Native"},
        "expectations": {
            "should_have_mb_data": True,
            "min_confidence": 0.5,
            "should_not_hallucinate": ["格莱美", "Billboard", "制作人"],
        },
    },
    {
        "name": "经典摇滚歌曲",
        "track": {"title": "Bohemian Rhapsody", "artist": "Queen", "album": "A Night at the Opera"},
        "expectations": {
            "should_have_mb_data": True,
            "min_confidence": 0.7,
            "should_not_hallucinate": ["格莱美", "Billboard"],
        },
    },
    {
        "name": "中文流行歌曲",
        "track": {"title": "晴天", "artist": "周杰伦", "album": "叶惠美"},
        "expectations": {
            "should_have_mb_data": True,
            "min_confidence": 0.5,
            "should_not_hallucinate": ["格莱美", "Billboard"],
        },
    },
    {
        "name": "独立音乐",
        "track": {"title": "Skinny Love", "artist": "Bon Iver", "album": "For Emma, Forever Ago"},
        "expectations": {
            "should_have_mb_data": True,
            "min_confidence": 0.5,
            "should_not_hallucinate": ["格莱美", "Billboard"],
        },
    },
    {
        "name": "电子音乐",
        "track": {"title": "Strobe", "artist": "Deadmau5", "album": "For Lack of a Better Name"},
        "expectations": {
            "should_have_mb_data": True,
            "min_confidence": 0.5,
            "should_not_hallucinate": ["格莱美", "Billboard"],
        },
    },
    {
        "name": "冷门歌曲（低置信度）",
        "track": {"title": "Test Song That Does Not Exist", "artist": "Unknown Artist", "album": "Unknown"},
        "expectations": {
            "should_have_mb_data": False,
            "min_confidence": 0.0,
        },
    },
]

QUALITY_METRICS = {
    "min_content_length": 300,
    "max_content_length": 2000,
    "required_fields": ["content", "emotion", "similar_songs", "rating", "schema_version"],
    "valid_factuality_levels": ["metadata_only", "grounded", "mixed"],
    "valid_analysis_basis": ["track_metadata", "provided_context", "external_evidence"],
}
