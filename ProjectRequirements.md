# **Multi-Agent RAG RPG**

## **Goal**

Build a small RPG engine where multiple AI agents role-play inside the world of a single long text corpus (eg [Romeo and Juliet](https://folger-main-site-assets.s3.amazonaws.com/uploads/2022/11/romeo-and-juliet_TXT_FolgerShakespeare.txt),[Hitchhiker guide to galaxy](https://moodle.gybon.cz/pluginfile.php/17370/mod_folder/content/0/The%20hitchhikers%20guide%20to%20the%20galaxy%20-%20Douglas%20Adams.txt?forcedownload=1)). All in-game facts, locations, items, and NPC knowledge must come from retrieval over that corpus. A rules checker agent checks for any  hallucinated events /characters not in the corpus..For this project, we will use only fictional content with some level of world building.

---

## **Requirements (what to build)**

### **1\) Data & Ingestion**

* **Corpus**: Use any public-domain long work (). Provide the raw text file in `/data/corpus.txt`.

* **Ingestion**:

  * The data can be ingested/converted to vector embeddings and also an index for doing BM25 ranking

  

### **2\) Retrieval & Grounding**

* **Hybrid retrieval**: BM25 \+ vector search with some kind of weighted merge logic between vectorDB and BM25   
* **Preprocessing**:  
  * Some simple custom query rewriting ( even if you use open ai ) is preferred. 

* **RAG metrics** (Eval): A test program that can calculate Recall (R@5) , MRR and  relevant tokens / total context tokens metrics for a specific sample data  and saves the result to a file. 

  

### **3\) Multi-Agent Game Loop** 

(Using [h2g2](https://h2g2.com/) as an example for this )

Implement a minimal but real **multi-agent loop** (one tick per player turn): 

A player starts off with setting the context from the story with a dialog or action mentioned in the book. 

Eg action: Arthur dent lies in front of a bulldozer 

Dialog: Arthur Dent says “there's an infinite number of monkeys outside who want to talk to us about this script for [Hamlet](https://www.goodreads.com/book/show/1420.Hamlet) they've worked out”

**Core agents :**

* **Narrator**: This Generates scene descriptions grounded in retrieved chunks corresponding to the user and provides the setting

* **ScenePlanner**: Turns player statement  into planning the immediate next scene, ( which npc character responds  . If there are no apt character response narrator takes over and describes the next action.scene.  
    
* **NPCManager**: Produces NPC dialogue grounded in text about that character (speaking style, , facts). Eg if it is H2G2 then Marvin the robot , talks in the self-pity tone. 

* **RulesReferee**: Enforces simple rules  and *rejects actions that contradict the corpus* (with a cited passage).  
    
   The game should allow for multi turn conversations with the player , so some session memory needs to be available .It can be a sliding window to efficiently use the tokens. 

### **4\) System Design & Service**

* Provide a **stateless HTTP API** (`fastapi` or `flask`) with endpoints:

  * `POST /ingest` → runs ingestion  or can be done offline in a script  if run locally

  * `POST /turn` → `{session_id, player_command}` → returns  the output of all agents for every turn   
  *   
  * `POST /new_game` → starts a new session

  * `GET /state/{session_id}` → current game state.( for observability)

* Concurrency: design for **N concurrent sessions**; no shared mutable globals.

* Observability: **structured logs** (JSON) 

  **Output**  
    
  Hosted in AWS/lambda  with a simple UI (web or terminal)  to send the player commands and see the response.   
     
  AND/OR  
  **Dockerfile** \+ `Makefile` with targets:  `for setup/test/ingest/eval`

  

---

## **Things to Note**

* **Model output** cannot become ground truth only the text corpus.   
* Can use gpt or gemini  
* Can use openai vectordb if needed but needed hybrid ranking & some custom query rewrite  
* The scripts need to be in python


