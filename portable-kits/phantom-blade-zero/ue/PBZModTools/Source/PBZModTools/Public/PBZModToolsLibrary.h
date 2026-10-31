#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "PBZModToolsLibrary.generated.h"

class USkeletalMesh;
class UPhysicsAsset;
class UAnimBlueprint;
class UMaterialInstanceConstant;
class UTexture;
class UAnimSequence;

UCLASS()
class UPBZModToolsLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/** Creates (or loads) a PhysicsAsset at PackagePath/Name with the given preview mesh. */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static UPhysicsAsset* CreatePhysicsAsset(const FString& PackagePath, const FString& Name, USkeletalMesh* PreviewMesh);

	/**
	 * Replaces all bodies and constraints. Json: {"bodies":[{"bone":"thigh_l","type":"capsule|sphere|box","center":[x,y,z],
	 * "rotation":[pitch,yaw,roll] or "quat":[x,y,z,w],"radius":r,"length":l,"extent":[x,y,z],"kinematic":true,"mass":kg,
	 * "lin_damp":d,"ang_damp":d}], "joints":[{"child":"a","parent":"b","swing1":deg,"swing2":deg,"twist":deg,
	 * "drive_stiffness":s,"drive_damping":d}], "disable_pairs":[["a","b"]]}. Shapes are in bone local space (cm).
	 * Joint frames come from the mesh reference pose (child bone origin), so a joint may connect any two bodies.
	 */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static FString BuildPhysicsAsset(UPhysicsAsset* PhysicsAsset, USkeletalMesh* Mesh, const FString& Json);

	/** Adds mesh-level curve metadata (UAnimCurveMetaData asset user data) flagging each curve name as a morph target curve. */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static FString SetMorphCurveMetaData(USkeletalMesh* Mesh, const TArray<FString>& CurveNames);

	/** JSON dump of the mesh reference skeleton (local transforms). */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static FString DumpRefSkeleton(USkeletalMesh* Mesh);

	/** Morph target names of the mesh. */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static TArray<FString> GetMorphTargetNames(USkeletalMesh* Mesh);

	/** Sets the post-process anim blueprint class on the mesh. */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static void SetPostProcessAnimBlueprint(USkeletalMesh* Mesh, UClass* AnimClass);

	/** Sets the physics asset on the mesh (works for placeholder physics assets without bodies). */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static void SetMeshPhysicsAsset(USkeletalMesh* Mesh, UPhysicsAsset* PhysicsAsset);

	/** JSON summary of LOD0 sections and material slots. */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static FString DumpSections(USkeletalMesh* Mesh);
	/**
	 * Material parameter overrides with an explicit association (0 global, 1 layer, 2 blend) and layer index, for parents
	 * built from material layers (the game's character materials). ClearAll drops every existing override first.
	 */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static void ClearMaterialInstanceParameters(UMaterialInstanceConstant* Instance);

	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static void SetMaterialTextureParameter(UMaterialInstanceConstant* Instance, const FString& Name, int32 Association, int32 Index, UTexture* Value);

	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static void SetMaterialScalarParameter(UMaterialInstanceConstant* Instance, const FString& Name, int32 Association, int32 Index, float Value);

	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static void SetMaterialVectorParameter(UMaterialInstanceConstant* Instance, const FString& Name, int32 Association, int32 Index, FLinearColor Value);

	/** JSON list of the instance's texture/scalar/vector overrides (name, association, index). */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static FString DumpMaterialInstanceParameters(UMaterialInstanceConstant* Instance);
	/**
	 * Chaos (legacy skeletal mesh) clothing on the LOD0 section whose material slot is Slot; the section itself is the
	 * simulation mesh. MaskJson: {"type":"plane"|"radial","anchors":[[x,y,z],..],"dir":[x,y,z],"d0":cm,"d1":cm} gives
	 * MaxDistance = clamp((t - d0) / (d1 - d0)) * MaxDistance with t = dot(p - anchor, dir) (plane) or the distance to
	 * the nearest anchor (radial), in mesh component space. Optional "backstop": {"distance":cm,"radius":cm,"axis":[x,y,z],
	 * "min_dot":d} adds backstop maps on the free particles whose normal points away from the vertical axis through "axis".
	 * Optional "sim_slot":"Name" simulates on that slot's section instead (disabled for rendering) and binds Slot's section to it.
	 * ConfigJson is applied onto the UChaosClothConfig.
	 */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static FString CreateClothFromSlot(USkeletalMesh* Mesh, const FString& Slot, const FString& Name, UPhysicsAsset* CollisionAsset,
		float MaxDistance, const FString& MaskJson, const FString& ConfigJson);

	/**
	 * Solver iterations and substeps (UChaosClothSharedSimConfig) of every clothing asset of the mesh; one solver runs all
	 * cloth of a component. Returns the number of assets changed.
	 */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static int32 SetClothSolver(USkeletalMesh* Mesh, int32 Iterations, int32 Substeps);

	/** Unbinds and removes every clothing asset of the mesh. */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static int32 RemoveAllClothing(USkeletalMesh* Mesh);

	/** Cast shadow on/off for every section (all LODs) whose material slot is Slot; returns the number of sections. */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static int32 SetSectionCastShadow(USkeletalMesh* Mesh, const FString& Slot, bool bCastShadow);

	/**
	 * Sets the LOD0 normal (TangentZ) deltas of every Dst morph target that Src also has to Src's deltas of the same
	 * vertex (0 where Src has none). Src and Dst must have the same LOD0 vertices (count and UV0 checked), e.g. the same
	 * mesh imported with a scaled base shape, whose morph normals the importer computes from the distorted shapes.
	 */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static FString CopyMorphTangents(USkeletalMesh* Src, USkeletalMesh* Dst);

	/** JSON per LOD0 morph target: delta count, max position delta, max / mean normal (TangentZ) delta, deltas with normal delta > 0.5. */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static FString DumpMorphTargets(USkeletalMesh* Mesh);

	/**
	 * Replaces the sequence's content by float curves only (no bone tracks), Length seconds at 30 fps. CurvesJson:
	 * {"CurveName": [[time, value], ...], ...}; smooth keys with flat tangents.
	 */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static FString SetCurveSequence(UAnimSequence* Sequence, float Length, const FString& CurvesJson);

	/**
	 * Rebuilds the AnimGraph as Copy Pose From Mesh (attached parent, curves) -> Layered Blend Per Bone with the looping
	 * Overlay sequence as the only blend pose, no branch filters, curves by max value -> Output, and compiles.
	 * With a GateClass the overlay's blend weight is the variable KarinBlinkWeight, set on Blueprint Initialize Animation
	 * to 1 if the owning actor's class name contains GateClass (case-insensitive), else 0 (the plain pose copy); a leading
	 * "!" inverts the test. The event graph is rebuilt for it.
	 * With a SlotName the copied pose first gets a montage slot from SlotRootBone down (a second pose copy -> Slot ->
	 * Layered Blend Per Bone with a branch filter on SlotRootBone, depth 0), as the game's Hun_CopyPose_Head.
	 * Always (optional) is a second looping curve overlay after the gated one, blended the same way at weight 1.
	 */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static FString BuildCopyPoseOverlayAnimBP(UAnimBlueprint* AnimBP, UAnimSequence* Overlay, const FString& GateClass,
		const FString& SlotName, const FString& SlotRootBone, UAnimSequence* Always);

	/**
	 * Editor check of an anim class: spawns a plain actor (class name "Actor") with a skeletal mesh component of Mesh
	 * running AnimClass in the editor world, ticks the animation for Seconds in Steps steps and returns JSON with the
	 * KarinBlinkWeight variable, the anim instance's value of Curve and the component's morph target weight of Curve.
	 */
	UFUNCTION(BlueprintCallable, Category = "PBZModTools")
	static FString TestCopyPoseAnim(UClass* AnimClass, USkeletalMesh* Mesh, float Seconds, int32 Steps, const FString& Curve);
};
