# Traces

Real availability and workload traces are not committed (size, licences). Loaders in Phase 2 will pull them into this folder.

| Trace | What it gives us | Access | Licence |
|---|---|---|---|
| SpotLake (arXiv 2202.02973) | AWS spot placement score, interruption ratio, price history | public dataset + repo | see repo |
| Google 2019 cluster traces | Task/collection events incl. evictions | `gs://clusterdata_2019_*` (no account) | citation-only |
| Failure Trace Archive (Javadi et al., JPDC 2013) | Host failure/availability logs for many systems | fta.scem.uws.edu.au | see site |
| SETI@home / BOINC host availability | Volunteer host on/off intervals (Javadi, Kondo et al., TPDS 2011) | via FTA / BOINC wiki | see site |
| Azure LLM Inference 2023 (Splitwise) | Request arrivals + input/output token counts | github.com/Azure/AzurePublicDataset | CC-BY |
| BurstGPT (KDD 2025) | 10.31M Azure OpenAI request traces over 213 days | github.com/HPMLL/BurstGPT | CC-BY-4.0 |
| Mooncake trace | Long-context serving requests | github.com/kvcache-ai/Mooncake | see repo |

Evaluation recipe: cross one **availability** trace (departure process per node) with one **workload** trace (arrivals + lengths). Verify licences before redistribution.
