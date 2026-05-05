## SECTION 1 : PROJECT TITLE
## NUS Smart Scheduler
An AI-Powered Multi-Agent Smart Event Scheduling System

---

## SECTION 2 : EXECUTIVE SUMMARY / PAPER ABSTRACT

University students and staff often struggle to manage lectures, meetings, personal activities, and campus travel within limited time. Traditional scheduling tools require manual input, lack contextual understanding, and cannot adapt to individual preferences or optimize across multiple constraints. As a result, users spend significant effort planning their day, yet still end up with inefficient schedules.

To solve this problem, we developed **NUS Smart Scheduler**, an AI-powered system that converts natural language descriptions into optimized daily schedules. The system supports both structured task input and conversational interaction, allowing users to plan their day in a flexible and intuitive manner. Schedules are displayed using timeline visualizations and multiple candidate plans can be compared easily.

The core of the system is a **multi-agent collaborative architecture**. DialogueAgent understands user intent and extracts tasks, KnowledgeAgent retrieves campus information via **RAG**, MemoryAgent loads personalized preferences, RerankerAgent improves the relevance of retrieved results, and SchedulingAgent generates optimized plans using a **custom-built solver**. All agents communicate through a shared global state and follow a ReAct-style reasoning and acting workflow, making the process interpretable and flexible.

To generate high-quality schedules, tasks are modeled in discrete time slots with **hard constraints**. A **hybrid greedy + local search solver** is implemented, supporting multiple optimization modes such as travel-first, preference-first, and compact-day. The system also features **adaptive learning**, continuously improving through memory, feedback, and personalized objective tuning.

Evaluation results show that our solver produces more feasible and user-centric schedules than baseline methods, with significantly lower travel cost and higher preference satisfaction. Reranker experiments demonstrate improved retrieval and ranking accuracy. To ensure system security and responsible AI practices, a dedicated **Guardrails Agent** is implemented as an independent security layer, providing prompt injection detection, PII filtering, and a structured AI Security Risk Register. A **GitHub Actions-based MLSecOps pipeline** automates security regression testing, dependency vulnerability scanning, and structured audit logging across the development lifecycle. With an intuitive frontend offering Solver Mode and Agent Mode, **NUS Smart Scheduler** provides an intelligent, personalized, and scalable solution for real-world academic scheduling.


 

---

## SECTION 3 : VIDEO OF SYSTEM MODELLING & USE CASE DEMO

 
 **System Demo Video**：
 https://nusu-my.sharepoint.com/:v:/g/personal/e1468110_u_nus_edu/IQAqWsTv9cmkRpJZhNJBbkkGAUaL7JTJfMGtDyUtAjMU3VA 
 https://nusu-my.sharepoint.com/:v:/g/personal/e1468110_u_nus_edu/IQBe7GqYX9FESZ3ZNuB0li6PAQSDt4fdqAzhfxViN4tCPUo

---

## SECTION 4 : USER GUIDE

For setup instructions, deployment options (local / Docker / Kubernetes / GKE), daily operations, and CI/CD configuration, refer to the **Deployment Guide**:

👉 [`deployment/README.md`](deployment/README.md)

The guide covers:
- Local development with Docker Compose
- Local Kubernetes deployment (Docker Desktop / k3s)
- Cloud deployment on GKE
- Accessing the frontend, backend API docs, Grafana, and Prometheus
- Monitoring stack (Prometheus + Grafana + Loki)
- CI/CD pipeline setup and GitHub Secrets configuration

For end-user instructions, refer to the appendix **\<Installation & User Guide\>** in the project report (GitHub Folder: `ProjectReport`).

---

## SECTION 6 : PROJECT REPORT / PAPER

Refer to the full project report in GitHub Folder: `ProjectReport`.

---

## SECTION 7 : MISCELLANEOUS

Refer to the `Miscellaneous` folder for additional resources.

Possible contents:
- Survey / Dataset
- UI Mockups / Prototype images
- PPT slides or presentation assets

---

**This project is part of the Artificial Intelligent Systems Programme at NUS-ISS.**