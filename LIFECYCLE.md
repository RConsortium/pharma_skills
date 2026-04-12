# Agent Skill Development Lifecycle

Welcome to the skill development lifecycle for the **Pharma Skills** repository. Developing a robust AI agent skill is similar to developing a software package, structured around four core phases: Design, Development, Evaluation, and Release.

---

## 1. Design Phase

The goal of the design phase is to define the exact boundaries, inputs, and expected outputs of a skill. 

All design information should be documented in a `DESIGN.md` file within the skill's directory. This file is intended for human review and should be updated continually as the skill evolves.

**Best Practices:**
* Keep it high-level and contained within a single page.
* Focus on the conceptual scope and expected inputs/outputs, avoiding low-level implementation details at this stage.

## 2. Development Phase

Once the design is complete, the actual configuration of the skill takes place.

* **Adhere to Standards:** Follow the official [Agent Skills Specification](https://agentskills.io/specification) to ensure broad compatibility across all LLM platforms.
* **Bootstrapping Tools:** It is highly recommended to leverage the official [skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) to automatically bootstrap the initial foundation and directory structure for your new skill.
* **Course Reference:** For a comprehensive video tutorial, see DeepLearning.AI's short course: [Agent Skills with Anthropic](https://www.deeplearning.ai/short-courses/agent-skills-with-anthropic/).

## 3. Evaluation Phase

Before a skill is deployed, it must be thoroughly tested against different LLMs (e.g., Claude Code, Gemini, Codex) to ensure safety, accuracy, and reliability.

* **Test Methodology:** Follow the official guidelines on [Evaluating Skills](https://agentskills.io/skill-creation/evaluating-skills). Test cases should be self-contained within the skill's directory structure.

* **Community Contributions:** Rely on GitHub Issues to propose, discuss, and implement new test cases or edge cases. 
  *(Example: See [Issue #3](https://github.com/RConsortium/pharma_skills/issues/3) for a community-driven test case in action).*

## 4. Release Phase

Once the skill consistently produces robust and validated statistical results, it is ready to be published and utilized globally.

* **Documentation:** Ensure the skill's local `README.md` is complete, clearly detailing its purpose and required parameters for the end user.
* **Licensing:** Ensure an MIT `LICENSE` file is included in the skill's folder to comply with the repository's open collaboration standards.
* **Integration:** Add the skill as a standalone folder at the root directory of this repository. Be sure to update the global `.gitignore` if the execution of your skill generates any temporary artifacts.
* **Pull Request:** Submit a Pull Request updating the central index table of the root `README.md` with your completed skill!
