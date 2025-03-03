#!/usr/bin/env python3

from os import listdir, makedirs, path, system, getpid
import numpy as np

np.seterr(divide="ignore", invalid="ignore")
import pickle as pkl
import hist as Hist
from matplotlib import pyplot as plt
import coffea.processor as processor
import awkward as ak
from coffea.nanoevents import NanoEventsFactory
from functools import partial
import psutil

processor.NanoAODSchema.warn_missing_crossrefs = False


def isClean(obj_A, obj_B, drmin=0.4):
    # From: https://github.com/oshadura/topcoffea/blob/master/topcoffea/modules/objects.py
    objB_near, objB_DR = obj_A.nearest(obj_B, return_metric=True)
    mask = ak.fill_none(objB_DR > drmin, True)
    return mask


class NanoProcessor(processor.ProcessorABC):
    def __init__(self, cfg):
        self.cfg = cfg
        self._year = self.cfg.dataset["year"]
        self._campaign = self.cfg.dataset["campaign"]
        self.verblvl = 0
        self.proc_type = "ul"

        print("Year and campaign:", self._year, self._campaign)

        axis = {
            # "dataset"     : Hist.axis.StrCategory([],      name="dataset", label="Primary dataset", growth=True),
            "LHE_Vpt": Hist.axis.Regular(
                100, 0, 400, name="LHE_Vpt", label="LHE V PT [GeV]"
            ),
            "LHE_HT": Hist.axis.Regular(
                100, 0, 1000, name="LHE_HT", label="LHE HT [GeV]"
            ),
            "wei": Hist.axis.Regular(100, -1000, 10000, name="wei", label="wei"),
            "wei_sign": Hist.axis.Regular(50, -2, 2, name="wei", label="wei"),
            "nlep": Hist.axis.Regular(12, 0, 6, name="nlep", label="nlep"),
            "lep_eta": Hist.axis.Regular(50, -5, 5, name="lep_eta", label="lep_eta"),
            "lep_pt": Hist.axis.Regular(50, 0, 500, name="lep_pt", label="lep_pt"),
            "dilep_m": Hist.axis.Regular(50, 50, 120, name="dilep_m", label="dilep_m"),
            "dilep_pt": Hist.axis.Regular(
                100, 0, 600, name="dilep_pt", label="dilep_pt"
            ),
            "njet25": Hist.axis.Regular(12, 0, 6, name="njet25", label="njet25"),
            "jet_eta": Hist.axis.Regular(50, -5, 5, name="jet_eta", label="jet_eta"),
            "jet_pt": Hist.axis.Regular(50, 0, 500, name="jet_pt", label="jet_pt"),
            "dijet_m": Hist.axis.Regular(50, 0, 1200, name="dijet_m", label="dijet_m"),
            "dijet_pt": Hist.axis.Regular(
                100, 0, 600, name="dijet_pt", label="dijet_pt"
            ),
            "dijet_dr": Hist.axis.Regular(50, 0, 5, name="dijet_dr", label="dijet_dr"),
            #'dijet_dr_neg': Hist.axis.Regular(50, 0, 5,    name="dijet_dr", label="dijet_dr")
        }

        self._accumulator = processor.dict_accumulator(
            {
                observable: Hist.Hist(var_axis, name="Counts", storage="Weight")
                for observable, var_axis in axis.items()
                if observable != "dataset"
            }
        )
        self._accumulator["cutflow"] = processor.defaultdict_accumulator(
            partial(processor.defaultdict_accumulator, int)
        )
        self._accumulator["sumw"] = 0

        print(
            "\t Init : ", psutil.Process(getpid()).memory_info().rss / 1024**2, "MB"
        )

    @property
    def accumulator(self):
        return self._accumulator

    def process(self, events):
        output = self.accumulator
        # print(output)

        dataset = events.metadata["dataset"]
        LHE_Vpt = events.LHE["Vpt"]
        LHE_HT = events.LHE["HT"]
        # LHE_Njets = events.LHE['LHE_Njets'] # Does not exist in NanoV2
        # print(LHE_Vpt)
        # We can define a new key for cutflow (in this case 'all events').
        # Then we can put values into it. We need += because it's per-chunk (demonstrated below)
        output["cutflow"][dataset]["all_events"] += ak.size(LHE_Vpt)
        output["cutflow"][dataset]["number_of_chunks"] += 1

        particles = events.GenPart
        # leptons = particles[ (np.abs(particles.pdgId) == 13) & (particles.status == 1) & (np.abs(particles.eta)<2.5) ]
        leptons = particles[
            ((np.abs(particles.pdgId) == 11) | (np.abs(particles.pdgId) == 13))
            & ak.fill_none((np.abs(particles.parent.pdgId) != 15), True)
            & (particles.status == 1)
            & (np.abs(particles.eta) < 2.5)
            & (particles.pt > 20)
        ]

        genjets = events.GenJet
        jets25 = genjets[(np.abs(genjets.eta) < 2.5) & (genjets.pt > 25)]

        LHEP = events.LHEPart
        LHEjets = LHEP[
            (
                (np.abs(LHEP.pdgId) == 1)
                | (np.abs(LHEP.pdgId) == 2)
                | (np.abs(LHEP.pdgId) == 3)
                | (np.abs(LHEP.pdgId) == 4)
                | (np.abs(LHEP.pdgId) == 5)
                | (np.abs(LHEP.pdgId) == 21)
            )
            & (LHEP.status == 1)
        ]
        LHE_Njets = ak.num(LHEjets)

        # print(dataset)
        if dataset in [
            "DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8",
            "DYJetsToMuMu_BornSuppressV3_TuneCP5_13TeV-powhegMiNNLO-pythia8-photos",
        ]:
            weight_nosel = events.genWeight
            #print("Special cases:", dataset)
        else:
            weight_nosel = np.sign(events.genWeight)

        if self.verblvl > 0:
            print("\n", dataset, "wei:", weight_nosel)

        output["sumw"] += np.sum(weight_nosel)

        output["LHE_Vpt"].fill(LHE_Vpt=LHE_Vpt, weight=weight_nosel)
        output["LHE_HT"].fill(LHE_HT=LHE_HT, weight=weight_nosel)

        output["wei"].fill(wei=weight_nosel, weight=weight_nosel)
        output["wei_sign"].fill(
            wei=weight_nosel / np.abs(weight_nosel), weight=weight_nosel
        )

        output["nlep"].fill(nlep=ak.num(leptons), weight=weight_nosel)

        dileptons = ak.combinations(leptons, 2, fields=["i0", "i1"])

        pt25 = (dileptons["i0"].pt > 25) | (dileptons["i1"].pt > 25)
        Zmass_cut = ((dileptons["i0"] + dileptons["i1"]).mass - 91.19) < 15
        Vpt_cut = (dileptons["i0"] + dileptons["i1"]).pt > 10
        dileptonMask = pt25 & Zmass_cut & Vpt_cut
        good_dileptons = dileptons[dileptonMask]

        vpt = (good_dileptons["i0"] + good_dileptons["i1"]).pt
        vmass = (good_dileptons["i0"] + good_dileptons["i1"]).mass

        two_lep = ak.num(good_dileptons) == 1

        if self.proc_type == "pre":
            # LHE_vpt_cut = (LHE_Vpt>=155) & (LHE_Vpt<=245)
            LHE_vpt_cut = (LHE_Vpt >= 255) & (LHE_Vpt <= 395)
        elif self.proc_type == "ul":
            LHE_vpt_cut = True

        # jets25['isClean'] = isClean(jets25, leptons, drmin=0.5)
        # j_isclean = isClean(jets25, leptons, drmin=0.5)
        # From: https://github.com/CoffeaTeam/coffea/discussions/497#discussioncomment-600052
        j_isclean = ak.all(jets25.metric_table(leptons) > 0.5, axis=2)
        # NB: this gives identical result to the isClean() fuction above

        # good_jets = jets
        good_jets = jets25[j_isclean]
        two_jets = ak.num(good_jets) >= 2

        # LHE_Njets_cut = (LHE_Njets>=0)
        selection_2l = two_lep
        selection_2l2j = two_lep & two_jets & LHE_vpt_cut
        # full_selection = two_lep & two_jets & Vpt_cut
        # full_selection = two_lep & two_jets & LHE_vpt_cut & vmass_cut
        # full_selection = two_lep & two_jets & vpt_cut & vmass_cut

        events_2l = events[selection_2l]
        events_2l2j = events[selection_2l2j]

        output["cutflow"][dataset]["events_2l"] += len(events_2l)
        output["cutflow"][dataset]["events_2l2j"] += len(events_2l2j)

        if dataset in [
            "DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8",
            "DYJetsToMuMu_BornSuppressV3_TuneCP5_13TeV-powhegMiNNLO-pythia8-photos",
        ]:
            weight_full = events_2l2j.genWeight
            weight_2l = events_2l.genWeight
        else:
            weight_full = np.sign(events_2l2j.genWeight)
            weight_2l = np.sign(events_2l.genWeight)
        # weight = np.ones(len(events_2l2j))
        weight2_full = np.repeat(np.array(weight_full), 2)
        weight2_2l = np.repeat(np.array(weight_2l), 2)
        # print("weight length:", len(weight), len(weight2))
        # print(leptons.eta[full_selection][:,0:2])

        output["njet25"].fill(njet25=ak.num(good_jets[selection_2l]), weight=weight_2l)

        dijets = good_jets[selection_2l2j]
        dijet = dijets[:, 0] + dijets[:, 1]

        dijet_pt = dijet.pt
        dijet_m = dijet.mass
        dijet_dr = dijets[:, 0].delta_r(dijets[:, 1])

        output["dilep_m"].fill(
            dilep_m=ak.flatten(vmass[selection_2l]), weight=weight_2l
        )
        output["dilep_pt"].fill(
            dilep_pt=ak.flatten(vpt[selection_2l]), weight=weight_2l
        )

        output["lep_eta"].fill(
            lep_eta=ak.flatten(leptons.eta[selection_2l][:, 0:2]), weight=weight2_2l
        )
        output["lep_pt"].fill(
            lep_pt=ak.flatten(leptons.pt[selection_2l][:, 0:2]), weight=weight2_2l
        )

        # output['dilep_m'].fill(dilep_m=ak.flatten(vmass[selection_2l2j]), weight=weight_full)
        # output['dilep_pt'].fill(dilep_pt=ak.flatten(vpt[selection_2l2j]), weight=weight_full)

        # output['lep_eta'].fill(lep_eta=ak.flatten(leptons.eta[selection_2l2j][:,0:2]), weight=weight2_full)
        # output['lep_pt'].fill(lep_pt=ak.flatten(leptons.pt[selection_2l2j][:,0:2]), weight=weight2_full)

        output["jet_eta"].fill(
            jet_eta=ak.flatten(good_jets.eta[selection_2l2j][:, 0:2]),
            weight=weight2_full,
        )
        output["jet_pt"].fill(
            jet_pt=ak.flatten(good_jets.pt[selection_2l2j][:, 0:2]), weight=weight2_full
        )

        output["dijet_dr"].fill(dijet_dr=dijet_dr, weight=weight_full)
        output["dijet_m"].fill(dijet_m=dijet_m, weight=weight_full)
        output["dijet_pt"].fill(dijet_pt=dijet_pt, weight=weight_full)

        ##print("Negative DRs:", dijet_dr[weight<0])
        ##print("Negative wei:", weight[weight<0])
        # neg_wei = np.abs(weight_full[weight_full<0])
        # neg_wei_dr = dijet_dr[weight_full<0]
        # output['dijet_dr_neg'].fill(dijet_dr=neg_wei_dr, weight=neg_wei)

        return {dataset: output}

    def postprocess(self, accumulator):
        return accumulator


def main():
    print("There is no main() usage of this script")


if __name__ == "__main__":
    main()
