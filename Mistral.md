```markdown
# Mistral AI Embeddings Guide

## 📌 Introduction

**Embeddings** are vectorial representations of text that capture semantic meaning in high-dimensional space.  
Mistral AI offers cutting-edge embeddings through its API for various NLP tasks like:
- Clustering
- Classification
- Paraphrase Detection
- Retrieval-augmented generation (RAG)

---

## 🧠 Mistral Embed API: Getting Started

```python
import os
from mistralai import Mistral

api_key = os.environ["MISTRAL_API_KEY"]
model = "mistral-embed"

client = Mistral(api_key=api_key)

embeddings_batch_response = client.embeddings.create(
    model=model,
    inputs=["Embed this sentence.", "As well as this one."],
)
```

**Response Sample:**

```python
EmbeddingResponse(
    id='...', object='list',
    data=[
        Data(object='embedding', embedding=[...], index=0),
        Data(object='embedding', embedding=[...], index=1)
    ],
    model='mistral-embed',
    usage=EmbeddingResponseUsage(prompt_tokens=15, total_tokens=15)
)
```

### 📐 Embedding Dimensions
```python
len(embeddings_batch_response.data[0].embedding)  # Output: 1024
```

---

## 📏 Distance Measures

Use Euclidean, Cosine, or Dot Product (since Mistral uses norm-1 vectors):

```python
from sklearn.metrics.pairwise import euclidean_distances

def get_text_embedding(inputs):
    embeddings_batch_response = client.embeddings.create(
        model=model,
        inputs=inputs
    )
    return embeddings_batch_response.data[0].embedding
```

### Example:

```python
sentences = [
    "A home without a cat...",
    "I think books are like people..."
]
embeddings = [get_text_embedding([t]) for t in sentences]

reference_sentence = "Books are mirrors..."
reference_embedding = get_text_embedding([reference_sentence])

for t, e in zip(sentences, embeddings):
    distance = euclidean_distances([e], [reference_embedding])
    print(t, distance)
```

---

## 🔁 Paraphrase Detection

```python
import itertools

sentences = [
    "Have a safe happy Memorial Day weekend everyone",
    "To all our friends at Whatsit Productions Films enjoy a safe happy Memorial Day weekend",
    "Where can I find the best cheese?",
]

sentence_embeddings = [get_text_embedding([t]) for t in sentences]

pairs = list(itertools.combinations(sentence_embeddings, 2))
text_pairs = list(itertools.combinations(sentences, 2))

for s, e in zip(text_pairs, pairs):
    print(s, euclidean_distances([e[0]], [e[1]]))
```

---

## 🧵 Batch Processing

```python
import pandas as pd

df = pd.read_csv(
    "https://raw.githubusercontent.com/mistralai/cookbook/main/data/Symptom2Disease.csv",
    index_col=0,
)

def get_embeddings_by_chunks(data, chunk_size):
    chunks = [data[x:x+chunk_size] for x in range(0, len(data), chunk_size)]
    responses = [client.embeddings.create(model=model, inputs=c) for c in chunks]
    return [d.embedding for r in responses for d in r.data]

df["embeddings"] = get_embeddings_by_chunks(df["text"].tolist(), 50)
df.head()
```

---

## 🖼 t-SNE Visualization

```python
import seaborn as sns
from sklearn.manifold import TSNE
import numpy as np

tsne = TSNE(n_components=2, random_state=0).fit_transform(np.array(df['embeddings'].to_list()))
ax = sns.scatterplot(x=tsne[:, 0], y=tsne[:, 1], hue=np.array(df['label'].to_list()))
sns.move_legend(ax, 'upper left', bbox_to_anchor=(1, 1))
```

---

## ⚖️ fastText Comparison

```python
import fasttext.util

fasttext.util.download_model('en', if_exists='ignore')
ft = fasttext.load_model('cc.en.300.bin')

df['fasttext_embeddings'] = df['text'].apply(lambda x: ft.get_word_vector(x).tolist())

tsne = TSNE(n_components=2, random_state=0).fit_transform(np.array(df['fasttext_embeddings'].to_list()))
ax = sns.scatterplot(x=tsne[:, 0], y=tsne[:, 1], hue=np.array(df['label'].to_list()))
sns.move_legend(ax, 'upper left', bbox_to_anchor=(1, 1))
```

---

## 🧠 Classification from Embeddings

```python
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

train_x, test_x, train_y, test_y = train_test_split(
    df["embeddings"], df["label"], test_size=0.2
)

scaler = StandardScaler()
train_x = scaler.fit_transform(train_x.to_list())
test_x = scaler.transform(test_x.to_list())

clf = LogisticRegression(random_state=0, C=1.0, max_iter=500).fit(
    train_x, train_y.to_list()
)

print(f"Precision: {100*np.mean(clf.predict(test_x) == test_y.to_list()):.2f}%")
```

### Predicting a New Input

```python
text = "I've been experiencing frequent headaches and vision problems."
clf.predict([get_text_embedding([text])])
```

---

## ⚖️ Classification Comparison with fastText

```python
train_x, test_x, train_y, test_y = train_test_split(
    df["fasttext_embeddings"], df["label"], test_size=0.2
)

scaler = StandardScaler()
train_x = scaler.fit_transform(train_x.to_list())
test_x = scaler.transform(test_x.to_list())

clf = LogisticRegression(random_state=0, C=1.0, max_iter=500).fit(
    train_x, train_y.to_list()
)

print(f"Precision: {100*np.mean(clf.predict(test_x) == test_y.to_list()):.2f}%")
```

---

## 🔍 Clustering

```python
from sklearn.cluster import KMeans

model = KMeans(n_clusters=24, max_iter=1000)
model.fit(df['embeddings'].to_list())
df["cluster"] = model.labels_

print(*df[df.cluster==23].text.head(3), sep='\n\n')
```

---

## 📥 Retrieval & RAG

Mistral embeddings excel in **retrieval** and **RAG (retrieval-augmented generation)** systems.

**Workflow:**
1. Embed your knowledge base (docs, wiki, etc.)
2. Store vectors in a vector DB
3. Embed user query
4. Retrieve similar vectors
5. Pass results to LLM for final response

Check Mistral’s RAG guide for full implementation details.

---

