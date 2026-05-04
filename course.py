@group.command(name="course", description="🏇 Course multijoueur (2-6 pers) : Le gagnant rafle toute la mise !")
    async def course(self, interaction: discord.Interaction, mise: int):
        solde_host = self.get_user(interaction.user.id)
        if mise < 50: return await interaction.response.send_message("❌ La mise minimale est de 50 €.", ephemeral=True)
        if solde_host < mise: return await interaction.response.send_message("❌ Tu n'as pas assez d'argent pour organiser cette course.", ephemeral=True)

        # --- ACTION : L'hôte paie sa place immédiatement ---
        self.update_money(interaction.user.id, -mise)

        embed = discord.Embed(
            title="🏇 GRANDE COURSE HIPPIQUE",
            description=(
                f"**{interaction.user.display_name}** organise une course !\n"
                f"💰 Mise par personne : **{self.fmt(mise)} €**\n\n"
                f"**Inscrits (1/6) :**\n• {interaction.user.display_name}"
            ),
            color=0x27ae60
        )
        embed.set_footer(text="L'organisateur doit lancer la course quand tout le monde est prêt.")

        class CourseView(discord.ui.View):
            def __init__(self, cog, host, mise):
                super().__init__(timeout=120) # 2 minutes pour recruter
                self.cog = cog
                self.participants = [host]
                self.mise = mise
                self.started = False

            async def on_timeout(self):
                if not self.started:
                    # REMBOURSEMENT si la course n'a pas commencé
                    for p in self.participants:
                        self.cog.update_money(p.id, self.mise)

            @discord.ui.button(label="Participer", emoji="🏇", style=discord.ButtonStyle.green)
            async def join(self, i: discord.Interaction, b: discord.ui.Button):
                if self.started: return await i.response.send_message("❌ La course a déjà commencé !", ephemeral=True)
                if i.user.id in [p.id for p in self.participants]: return await i.response.send_message("❌ Tu es déjà sur ton cheval !", ephemeral=True)
                if len(self.participants) >= 6: return await i.response.send_message("❌ L'écurie est complète (6/6) !", ephemeral=True)
                
                s = self.cog.get_user(i.user.id)
                if s < self.mise: return await i.response.send_message("❌ Tu n'as pas les fonds pour miser.", ephemeral=True)

                # --- ACTION : Le participant paie immédiatement ---
                self.cog.update_money(i.user.id, -self.mise)
                self.participants.append(i.user)
                
                n = len(self.participants)
                emb = i.message.embeds[0]
                emb.description = f"**Organisateur :** {self.participants[0].display_name}\n💰 Mise : **{self.cog.fmt(self.mise)} €**\n\n**Inscrits ({n}/6) :**\n" + "\n".join([f"• {p.display_name}" for p in self.participants])
                await i.response.edit_message(embed=emb, view=self)

            @discord.ui.button(label="Lancer !", emoji="🚩", style=discord.ButtonStyle.blurple)
            async def start(self, i: discord.Interaction, b: discord.ui.Button):
                if i.user.id != self.participants[0].id: return await i.response.send_message("❌ Seul l'organisateur peut donner le départ.", ephemeral=True)
                if len(self.participants) < 2: return await i.response.send_message("❌ Il faut au moins 2 coureurs pour lancer !", ephemeral=True)
                
                self.started = True
                self.clear_items()
                await i.response.edit_message(content="🚦 **PRÊTS ? LES PORTES S'OUVRENT !**", view=self)

                # Animation stylée
                pistes = {p.display_name: 0 for p in self.participants}
                for _ in range(4):
                    await asyncio.sleep(1.5)
                    for p in pistes: pistes[p] += random.randint(1, 4)
                    progression = "\n".join([f"🏇 | {'—' * pistes[p]} **{p}**" for p in pistes])
                    await i.edit_original_response(content=f"🏁 **LA COURSE BAT SON PLEIN !**\n\n{progression}")

                # Résultat
                gagnant = random.choice(self.participants)
                cagnotte = self.mise * len(self.participants)
                
                # --- ACTION : On donne la cagnotte au gagnant ---
                self.cog.update_money(gagnant.id, cagnotte)

                res = discord.Embed(
                    title="🏆 RÉSULTAT DE LA COURSE",
                    description=(
                        f"Photo-finish incroyable ! 📸\n\n"
                        f"Le cheval de **{gagnant.mention}** gagne d'une courte tête !\n"
                        f"💰 Il repart avec la cagnotte de **{self.cog.fmt(cagnotte)} €** !"
                    ),
                    color=0xF1C40F
                )
                await i.edit_original_response(content=None, embed=res)

            @discord.ui.button(label="Annuler", emoji="🚫", style=discord.ButtonStyle.secondary)
            async def cancel(self, i: discord.Interaction, b: discord.ui.Button):
                if i.user.id != self.participants[0].id: return await i.response.send_message("❌ Seul l'organisateur peut annuler.", ephemeral=True)
                self.started = True # Pour stopper le timeout
                for p in self.participants:
                    self.cog.update_money(p.id, self.mise)
                await i.response.edit_message(content="❌ Course annulée. Tout le monde a été remboursé.", embed=None, view=None)

        await interaction.response.send_message(embed=embed, view=CourseView(self, interaction.user, mise))
