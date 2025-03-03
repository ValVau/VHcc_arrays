# Local Variables:
# python-indent-offset: 4
# End:

from VHcc.workflows.Zll_process import (
    NanoProcessor as VH_Zll,
)

cfg = {
    "userconfig": {'version':'test_nolepsf'},
    "dataset": {
        "jsons": ["src/VHcc/metadata/mcsamples_2017_vjets_Zll_used_nonCorruptedOnly.json",
                  "src/VHcc/metadata/mcsamples_2017_vjets_ext_Zll_used_nonCorruptedOnly.json",
                  "src/VHcc/metadata/mcsamples_2017_other_Zll_used_nonCorruptedOnly.json",
                  "src/VHcc/metadata/mcsamples_2017_higgs_Zll_used.json",
                  "src/VHcc/metadata/datasamples_2017_Zll_used.json"],
        "campaign": "UL17",
        "year": "2017",
        "filter": {
            "samples": [
                "DYJetsToLL_nlo",
                #"DY1ToLL_PtZ-250To400",
                #"DY1ToLL_PtZ-50To150",
                #"DY1ToLL_PtZ-150To250",
                #"DY1ToLL_PtZ-400ToInf",
                #"DY2ToLL_PtZ-50To150",
                #"DY2ToLL_PtZ-150To250",
                #"DY2ToLL_PtZ-250To400",
                #"DY2ToLL_PtZ-400ToInf",
                #"",
                #"",
                #"",
            ],
            "samples_exclude": [],
        },
    },
    # Input and output files
    "workflow": VH_Zll,
    "output": "output_vhcc_zll",
    "run_options": {
        #"executor": "parsl/condor",
        "executor": "futures",
        "workers": 10,
        "scaleout": 10,
        "walltime": "03:00:00",
        "mem_per_worker": 2,  # GB
        "chunk": 50000,
        "max": None,
        "skipbadfiles": True,
        "voms": None,
        "limit": 1,
        "retries": 20,
        "splitjobs": False,
    },
}
