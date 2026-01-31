from transformers import pipeline
classifier = pipeline("zero-shot-classification",
                      model="facebook/bart-large-mnli")

sequence_to_classify = "Any window for windy areas?"
candidate_labels = ['Product consultation', 'Product Recommendation', "Price Consultation", "Company Introduction", "Others"]
res = classifier(sequence_to_classify, candidate_labels)
# ✅ 在程序启动时只加载一次
print("正在初始化模型...")
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
print("模型加载完成！")

def get_intent(text):
    # 直接使用已经加载好的全局变量
    return classifier(text, candidate_labels)
print(res)
