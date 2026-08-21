from __future__ import annotations
import unittest
from datetime import datetime, timezone
from searchleads.domain import ContactKind, ContactStatus, Evidence, Person
from searchleads.person_professional_contacts import discover_person_professional_channels, build_person_contact_points, persist_person_contact_points

URL="https://example.org/people"
NOW=datetime(2026,8,21,17,0,tzinfo=timezone.utc)

class PersonProfessionalContactTests(unittest.TestCase):
    def test_two_people_keep_channels_in_their_own_blocks(self):
        html="""<h2>Diretor</h2><p>Ana Silva</p><p>Telefone: (61) 2021-8101</p><p>E-mail: ana@example.org</p><h2>Diretor</h2><p>Bruno Costa</p><p>Telefone: (61) 2021-8133</p><p>E-mail: bruno@example.org</p>"""
        r=discover_person_professional_channels(URL,html,["Ana Silva","Bruno Costa"])
        got={(x.person_name,x.kind,x.value) for x in r.channels}
        self.assertIn(("Ana Silva",ContactKind.EMAIL,"ana@example.org"),got)
        self.assertIn(("Bruno Costa",ContactKind.PHONE,"(61) 2021-8133"),got)
        self.assertNotIn(("Ana Silva",ContactKind.EMAIL,"bruno@example.org"),got)

    def test_shared_curriculum_url_is_not_promoted_to_person_profile(self):
        html="""<p>Ana Silva</p><a href='/curriculos'>Currículo</a><p>Bruno Costa</p><a href='/curriculos'>Currículo</a>"""
        r=discover_person_professional_channels(URL,html,["Ana Silva","Bruno Costa"])
        self.assertFalse(any(x.kind is ContactKind.PROFESSIONAL_PROFILE for x in r.channels))
        self.assertEqual(r.shared_profile_locators,("https://example.org/curriculos",))

    def test_unique_profile_links_are_emitted(self):
        html="""<p>Ana Silva</p><a href='/curriculos/ana'>Currículo</a><p>Bruno Costa</p><a href='/curriculos/bruno'>Currículo</a>"""
        r=discover_person_professional_channels(URL,html,["Ana Silva","Bruno Costa"])
        profiles={(x.person_name,x.value) for x in r.channels if x.kind is ContactKind.PROFESSIONAL_PROFILE}
        self.assertEqual(profiles,{("Ana Silva","https://example.org/curriculos/ana"),("Bruno Costa","https://example.org/curriculos/bruno")})

    def test_incomplete_phone_is_rejected(self):
        html="<p>Ana Silva</p><p>Telefone: (61)</p><p>E-mail: ana@example.org</p>"
        r=discover_person_professional_channels(URL,html,["Ana Silva"])
        self.assertFalse(any(x.kind is ContactKind.PHONE for x in r.channels))
        self.assertTrue(any(x.kind is ContactKind.EMAIL for x in r.channels))

    def test_contact_points_are_person_owned_discovered_observations(self):
        html="<p>Ana Silva</p><p>E-mail: ana@example.org</p>"
        r=discover_person_professional_channels(URL,html,["Ana Silva"])
        ev=Evidence("e1","s1",NOW,{"body":html})
        contacts=build_person_contact_points({"Ana Silva":Person("p1",NOW)},ev,r)
        self.assertEqual(len(contacts),1)
        self.assertEqual(contacts[0].owner.entity_id,"p1")
        self.assertEqual(contacts[0].status,ContactStatus.DISCOVERED)
        self.assertEqual(contacts[0].provenance.evidence_ids,("e1",))

    def test_contact_points_can_be_persisted_through_store_boundary(self):
        html="<p>Ana Silva</p><p>E-mail: ana@example.org</p>"
        r=discover_person_professional_channels(URL,html,["Ana Silva"])
        ev=Evidence("e1","s1",NOW,{"body":html})
        contacts=build_person_contact_points({"Ana Silva":Person("p1",NOW)},ev,r)
        class Store:
            def __init__(self): self.saved=[]
            def save_contact_point(self, contact): self.saved.append(contact)
        store=Store()
        persist_person_contact_points(store,contacts)
        self.assertEqual(store.saved,list(contacts))

    def test_unknown_page_person_does_not_create_contact(self):
        html="<p>Other Person</p><p>E-mail: other@example.org</p>"
        r=discover_person_professional_channels(URL,html,["Ana Silva"])
        self.assertEqual(r.channels,())

    def test_duplicate_visible_email_is_deduped(self):
        html="<p>Ana Silva</p><p>E-mail: ana@example.org</p><p>ana@example.org</p>"
        r=discover_person_professional_channels(URL,html,["Ana Silva"])
        emails=[x for x in r.channels if x.kind is ContactKind.EMAIL]
        self.assertEqual(len(emails),1)

    def test_serpro_directors_fixture_exposes_fourteen_professional_channels(self):
        html="""
        <p>Wilton Itaiguara Gonçalves Mota</p><p>Telefone: (61) 2021-8101</p><p>E-mail: presidencia@serpro.gov.br</p><a href='/acesso-a-informacao/institucional/quem-e-quem/curriculos_diretoria_assessores/'>Currículo</a>
        <p>Ermes Ferreira Costa Neto</p><p>Telefone: (61) 2021-8133</p><p>E-mail: dingm@serpro.gov.br</p><a href='/acesso-a-informacao/institucional/quem-e-quem/curriculos_diretoria_assessores/'>Currículo</a>
        <p>Wallyson Lemos dos Reis Oliveira</p><p>Telefone: (61) 2021-8330</p><p>E-mail: diinf@serpro.gov.br</p><a href='/acesso-a-informacao/institucional/quem-e-quem/curriculos_diretoria_assessores/'>Currículo</a>
        <p>Osmar Quirino da Silva</p><p>Telefone: (61) 2021-8133</p><p>E-mail: diraf@serpro.gov.br</p><a href='/acesso-a-informacao/institucional/quem-e-quem/curriculos_diretoria_assessores/'>Currículo</a>
        <p>Alexandre Brandão Henriques Maimoni</p><p>Telefone: (61) 2021-8330</p><p>E-mail: dipej@serpro.gov.br</p><a href='/acesso-a-informacao/institucional/quem-e-quem/curriculos_diretoria_assessores/'>Currículo</a>
        <p>Ariadne de Santa Teresa Lopes Fonseca</p><p>Telefone: (61) 2021-8330</p><p>E-mail: dinef@serpro.gov.br</p><a href='/acesso-a-informacao/institucional/quem-e-quem/curriculos_diretoria_assessores/'>Currículo</a>
        <p>André Picoli Agatte</p><p>Telefone: (61) 2021-8133</p><p>E-mail: dinit@serpro.gov.br</p><a href='/acesso-a-informacao/institucional/quem-e-quem/curriculos_diretoria_assessores/'>Currículo</a>
        """
        names=[
            "Wilton Itaiguara Gonçalves Mota","Ermes Ferreira Costa Neto","Wallyson Lemos dos Reis Oliveira",
            "Osmar Quirino da Silva","Alexandre Brandão Henriques Maimoni","Ariadne de Santa Teresa Lopes Fonseca","André Picoli Agatte"
        ]
        r=discover_person_professional_channels("https://www.transparencia.serpro.gov.br/acesso-a-informacao/institucional/quem-e-quem",html,names)
        self.assertEqual(len([x for x in r.channels if x.kind in {ContactKind.EMAIL,ContactKind.PHONE}]),14)
        self.assertFalse(any(x.kind is ContactKind.PROFESSIONAL_PROFILE for x in r.channels))
        self.assertEqual(len(r.shared_profile_locators),1)

if __name__=='__main__': unittest.main()
